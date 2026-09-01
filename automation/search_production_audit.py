"""AST call-graph closure audit for the indexed-search production tranche.

The audit is a report, not an import-and-run smoke test.  It parses the
automation Python tree, follows local and imported call sites, identifies CLI
or connector registrations as roots, and reports exported production
callables that have no path from one of those roots.  Tests are not graph
roots, and dataclass value records are admitted only with an explicit
``production-audit: pure-value`` annotation or an entry in the table below.
"""

from __future__ import annotations

import ast
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional

try:  # package imports
    from .search_types import hash_canonical
except ImportError:  # direct invocation from the automation directory
    from automation.search_types import hash_canonical  # type: ignore


PRODUCTION_AUDIT_PROTOCOL = "sotn-search-production-audit-v1"

# This is intentionally a table of identities, not a naming convention.  A
# value type may be pure even when its name does not end in ``Record`` and a
# callable must not become pure merely because it looks like a constructor.
PURE_VALUE_EXPORTS = frozenset(
    {
        "automation.search_production_audit.LaneClosureFinding",
        "automation.search_production_audit.ProductionAuditReport",
        "automation.search_production_audit.ProductionExport",
        "automation.search_archive.ArtifactRef",
        "automation.search_donor_index.DonorRevision",
        "automation.search_donor_index.DonorIndexBinding",
        "automation.search_donor_index.DonorIndexEntry",
        "automation.search_donor_index.DonorIndexGeneration",
        "automation.search_donor_query.DonorAmbiguityReceipt",
        "automation.search_donor_query.DonorIncompatibilityReceipt",
        "automation.search_donor_query.DonorQuery",
        "automation.search_donor_query.DonorQueryHit",
        "automation.search_donor_query.DonorQueryResult",
        "automation.search_donor_query.DonorSemanticClaim",
        "automation.search_donor_query.DonorStaleReceipt",
        "automation.search_evidence_corpus.AbsenceMaskingClaim",
        "automation.search_evidence_corpus.CompletedLineageContext",
        "automation.search_evidence_corpus.CompletedLineageDiagnostic",
        "automation.search_evidence_corpus.CorpusEvidence",
        "automation.search_evidence_corpus.CorpusGeneration",
        "automation.search_evidence_corpus.EvidenceRefusalReceipt",
        "automation.search_evidence_corpus.LessonCitation",
        "automation.search_evidence_corpus.PromotionAccepted",
        "automation.search_evidence_corpus.PromotionRefused",
        "automation.search_evidence_corpus.ScorerTaxonomy",
        "automation.search_lanes.DonorEvidence",
        "automation.search_lanes.LaneAdapters",
        "automation.search_lanes.LaneBatch",
        "automation.search_lanes.LaneCandidate",
        "automation.search_lanes.LaneContext",
        "automation.search_lanes.LaneEvidence",
        "automation.search_lanes.LaneOutcome",
        "automation.search_lanes.LaneReceiptProposal",
        "automation.search_lanes.LaneRefusal",
        "automation.search_lanes.LaneRun",
        "automation.search_lanes.Recipient",
        "automation.search_lanes.StructuralTriangulation",
        "automation.search_patterns.CompletedLineageContext",
        "automation.search_patterns.CompletedLineageDiagnostic",
        "automation.search_patterns.SearchPatternReport",
        "automation.search_semantic_signatures.SemanticClassification",
        "automation.search_semantic_signatures.SemanticInstruction",
        "automation.search_types.ArtifactRef",
        "automation.search_types.ArchiveDecision",
        "automation.search_types.Budget",
        "automation.search_types.CandidateRecord",
        "automation.search_types.Checkpoint",
        "automation.search_types.EvaluationEvent",
        "automation.search_types.ExhaustionReceipt",
        "automation.search_types.FirstDivergence",
        "automation.search_types.GroupedPatch",
        "automation.search_types.Interruption",
        "automation.search_types.LedgerEvent",
        "automation.search_types.MutationEvent",
        "automation.search_types.OracleReceipt",
        "automation.search_types.OracleRequest",
        "automation.search_types.ParentRun",
        "automation.search_types.PatchHunk",
        "automation.search_types.RunManifest",
        "automation.search_types.RunResume",
        "automation.search_types.RunStop",
        "automation.search_types.ScoreComponents",
        "automation.search_types.ScoreDeltas",
        "automation.search_types.ScoreVector",
        "automation.search_types.SearchTask",
        "automation.search_types.TaskTerminal",
        "automation.search_supervisor.IntegrationGateReceipt",
    }
)
PURE_VALUE_EXPORT_ANNOTATIONS = MappingProxyType(
    {name: "pure-value" for name in sorted(PURE_VALUE_EXPORTS)}
)
PURE_VALUE_ANNOTATIONS = PURE_VALUE_EXPORT_ANNOTATIONS

# These are the modules introduced by the indexed-search tranche.  Unknown
# files named ``search_*`` and explicit ``tranche`` fixtures are included as
# well, which keeps the audit useful in a miniature repository without making
# every historical automation helper part of this gate.
TRANCHE_MODULES = frozenset(
    {
        "automation.search_archive",
        "automation.search_donor_index",
        "automation.search_donor_query",
        "automation.search_donor_scan",
        "automation.search_evidence_corpus",
        "automation.search_indexed_lane",
        "automation.search_lanes",
        "automation.search_patterns",
        "automation.search_production_audit",
        "automation.search_semantic_signatures",
        "automation.search_supervisor",
        "automation.search_types",
    }
)

EXPECTED_LANE_CLOSURE_GAPS = (
    "m2c_ensemble",
    "idiom_atlas",
    "bounded_synthesis",
    "permuter_random",
    "permuter_targeted",
    "permuter_recombine",
    "permuter_ddmin",
    "model_fleet",
    "model_expensive",
)

# The core dispatcher has concrete implementations for these lanes.  Keeping
# this as an audit-side protocol value is deliberate: adding an ``if`` branch
# for a new lane cannot make its factory or runtime closure disappear unless
# the new lane is explicitly bound here or in the immutable external-lane
# registry parsed below.
_CORE_FACTORY_LANES = frozenset(
    {
        "upstream_current",
        "upstream_pinned",
        "upstream_open_pr",
        "mipsmatch_exact",
        "preserved_candidate",
        "shared_header",
        "transplant",
        "whole_tu",
        "dependency_closure",
        "multi_donor",
        "cfg_dataflow",
    }
)

# A direct built-in dispatch branch is accepted only for the known concrete
# discovery implementations. A branch that merely calls a generic provider
# helper is not enough to close a lane.
_DIRECT_DISPATCH_PROVIDER_NAMES = frozenset(
    {
        "_upstream_discovery",
        "_preserved_discovery",
        "_shared_header_discovery",
        "_twin_discovery",
        "_whole_tu_discovery",
        "_dependency_discovery",
        "_structural_discovery",
        "_mipsmatch_discovery",
    }
)
_PROVIDER_REGISTRY_SUFFIXES = (
    "_PROVIDER_REGISTRY",
    "_ADAPTER_REGISTRY",
    "_PROVIDERS",
    "_ADAPTERS",
)
_RUNTIME_ADAPTER_FACTORY_NAMES = frozenset(
    {
        "production_indexed_adapters",
        "reconstruct_production_adapters",
        "reconstruct_lane_adapters",
        "build_lane_adapters",
        "load_production_adapters",
        "provider_adapters",
    }
)
_RUNTIME_REVALIDATION_NAMES = frozenset(
    {
        "verify_factory_runtime",
        "verify_indexed_runtime",
        "load_indexed_runtime",
        "validate_runtime_binding",
        "revalidate_runtime_binding",
        "verify_lane_provider",
        "revalidate_lane_provider",
    }
)


class ProductionAuditError(RuntimeError):
    """The audit could not parse or inspect the supplied repository."""


@dataclass(frozen=True)
class ProductionExport:
    """One exported tranche definition and its production reachability."""

    identity: str
    module: str
    name: str
    kind: str
    classification: str
    annotation: Optional[str]
    callers: tuple[str, ...]
    caller_chain: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "module": self.module,
            "name": self.name,
            "kind": self.kind,
            "classification": self.classification,
            "annotation": self.annotation,
            "callers": list(self.callers),
            "caller_chain": list(self.caller_chain),
        }


@dataclass(frozen=True)
class LaneClosureFinding:
    """One advertised lane that is not closed through production surfaces."""

    lane: str
    missing_dispatcher: bool
    missing_factory_tool_binding: bool
    missing_provider_input: bool
    missing_cli_connector_reachability: bool
    categories: tuple[str, ...]
    cli_reachable: bool = False
    connector_reachable: bool = False
    missing_supervisor_reachability: bool = False
    missing_recovery_reachability: bool = False
    missing_factory_module: bool = False
    missing_factory_tool: bool = False
    missing_factory_input: bool = False
    missing_provider_module: bool = False
    missing_provider_adaptor: bool = False

    @property
    def missing_factory_binding(self) -> bool:
        return self.missing_factory_tool_binding

    @property
    def missing_cli_reachability(self) -> bool:
        return not self.cli_reachable

    @property
    def missing_connector_reachability(self) -> bool:
        return not self.connector_reachable

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "missing_dispatcher": self.missing_dispatcher,
            "missing_factory_tool_binding": self.missing_factory_tool_binding,
            "missing_factory_module": self.missing_factory_module,
            "missing_factory_tool": self.missing_factory_tool,
            "missing_factory_input": self.missing_factory_input,
            "missing_provider_input": self.missing_provider_input,
            "missing_provider_module": self.missing_provider_module,
            "missing_provider_adaptor": self.missing_provider_adaptor,
            "missing_cli_connector_reachability": self.missing_cli_connector_reachability,
            "missing_supervisor_reachability": self.missing_supervisor_reachability,
            "missing_recovery_reachability": self.missing_recovery_reachability,
            "missing_cli_reachability": self.missing_cli_reachability,
            "missing_connector_reachability": self.missing_connector_reachability,
            "cli_reachable": self.cli_reachable,
            "connector_reachable": self.connector_reachable,
            "categories": list(self.categories),
        }


@dataclass(frozen=True)
class ProductionAuditReport:
    """Immutable result of :func:`audit_production_exports`."""

    exports: tuple[ProductionExport, ...]
    unreachable_exports: tuple[str, ...]
    annotation_errors: tuple[str, ...]
    caller_chains: Mapping[str, tuple[str, ...]]
    production_roots: tuple[str, ...]
    identity: str
    lane_findings: tuple[LaneClosureFinding, ...] = ()
    lane_closure_errors: tuple[str, ...] = ()
    protocol: str = PRODUCTION_AUDIT_PROTOCOL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "caller_chains",
            MappingProxyType(
                {
                    str(key): tuple(value)
                    for key, value in self.caller_chains.items()
                }
            ),
        )

    @property
    def passed(self) -> bool:
        return (
            not self.unreachable_exports
            and not self.annotation_errors
            and not self.lane_closure_errors
        )

    @property
    def ok(self) -> bool:
        return self.passed

    @property
    def orphan_exports(self) -> tuple[str, ...]:
        return self.unreachable_exports

    @property
    def stranded_exports(self) -> tuple[str, ...]:
        return self.unreachable_exports

    @property
    def missing_production_callers(self) -> tuple[str, ...]:
        return self.unreachable_exports

    @property
    def missing_callers(self) -> tuple[str, ...]:
        return self.unreachable_exports

    @property
    def unreachable(self) -> tuple[str, ...]:
        return self.unreachable_exports

    @property
    def unclosed_lanes(self) -> tuple[LaneClosureFinding, ...]:
        return self.lane_findings

    @property
    def lane_gaps(self) -> tuple[LaneClosureFinding, ...]:
        return self.lane_findings

    @property
    def lane_closure_by_lane(self) -> Mapping[str, LaneClosureFinding]:
        return MappingProxyType({item.lane: item for item in self.lane_findings})

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "identity": self.identity,
            "exports": [item.to_dict() for item in self.exports],
            "unreachable_exports": list(self.unreachable_exports),
            "annotation_errors": list(self.annotation_errors),
            "caller_chains": {
                key: list(value)
                for key, value in sorted(self.caller_chains.items())
            },
            "production_roots": list(self.production_roots),
            "lane_findings": [item.to_dict() for item in self.lane_findings],
            "lane_closure_errors": list(self.lane_closure_errors),
            "passed": self.passed,
        }


@dataclass(frozen=True)
class _Definition:
    module: str
    name: str
    kind: str
    node: ast.AST
    path: Path
    source_lines: tuple[str, ...]
    decorators: tuple[str, ...]
    dataclass: bool
    frozen_dataclass: bool
    annotation: Optional[str]

    @property
    def identity(self) -> str:
        return self.module + "." + self.name


@dataclass
class _Module:
    name: str
    path: Path
    tree: ast.Module
    source_lines: tuple[str, ...]
    exports: tuple[_Definition, ...]
    definitions: dict[str, _Definition]
    from_imports: dict[str, tuple[str, str]]
    module_imports: dict[str, str]
    roots: set[str]


def _as_repo(repo: Path | str) -> Path:
    try:
        root = Path(repo).resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ProductionAuditError("repository root cannot be resolved") from exc
    if not root.is_dir():
        raise ProductionAuditError("repository root must be a directory")
    return root


def _module_name(path: Path, *, repo: Path, automation: Path) -> str:
    relative = path.relative_to(repo).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[0] == automation.name:
        parts[0] = "automation"
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _decorator_name(value: ast.AST) -> str:
    if isinstance(value, ast.Call):
        value = value.func
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return _decorator_name(value.value) + "." + value.attr
    return ""


def _has_marker(lines: Sequence[str], line_number: int, marker: str) -> bool:
    start = max(0, line_number - 4)
    end = min(len(lines), line_number)
    accepted = {marker.strip(), "# " + marker.strip().lstrip("#").strip()}
    return any(lines[index].strip() in accepted for index in range(start, end))


def _dataclass_traits(
    node: ast.AST,
    decorators: Sequence[str],
) -> tuple[bool, bool]:
    if not isinstance(node, ast.ClassDef):
        return False, False
    dataclass = False
    frozen = False
    for decorator_node in node.decorator_list:
        if _decorator_name(decorator_node).rsplit(".", 1)[-1] != "dataclass":
            continue
        dataclass = True
        if isinstance(decorator_node, ast.Call):
            frozen = any(
                keyword.arg == "frozen"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in decorator_node.keywords
            )
    return dataclass, frozen


def _structurally_immutable_dataclass(definition: _Definition) -> bool:
    """Accept only frozen records with no obvious mutable field or mutator."""

    if not definition.dataclass or not definition.frozen_dataclass:
        return False
    return _structurally_immutable_class(definition.node)


def _structurally_immutable_class(node: ast.AST) -> bool:
    """Return whether a class has a statically immutable record shape."""

    if not isinstance(node, ast.ClassDef):
        return False
    mutable_names = {
        "list",
        "List",
        "dict",
        "Dict",
        "set",
        "Set",
        "bytearray",
        "deque",
        "defaultdict",
        "OrderedDict",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
    }
    mutating_methods = {
        "add",
        "append",
        "clear",
        "discard",
        "extend",
        "insert",
        "pop",
        "remove",
        "reverse",
        "sort",
        "update",
        "__delattr__",
        "__delitem__",
        "__setattr__",
        "__setitem__",
    }
    for statement in node.body:
        if isinstance(statement, ast.AnnAssign):
            names = {
                item.id
                for item in ast.walk(statement.annotation)
                if isinstance(item, ast.Name)
            }
            if names.intersection(mutable_names):
                return False
            value = statement.value
            if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                return False
            if isinstance(value, ast.Call):
                if _call_target_name(value.func) in mutable_names:
                    return False
                if any(
                    keyword.arg == "default_factory"
                    and not (
                        isinstance(keyword.value, ast.Name)
                        and keyword.value.id in {"tuple", "frozenset"}
                    )
                    for keyword in value.keywords
                ):
                    return False
        elif isinstance(statement, ast.Assign):
            if isinstance(statement.value, (ast.List, ast.Dict, ast.Set)):
                return False
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if statement.name in {"__setattr__", "__delattr__"}:
                return False
            for child in ast.walk(statement):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    receiver = child.func.value
                    while isinstance(receiver, (ast.Attribute, ast.Subscript)):
                        receiver = receiver.value
                    mutates_record = (
                        isinstance(receiver, ast.Name)
                        and receiver.id in {"self", "cls"}
                    )
                    if child.func.attr in mutating_methods and mutates_record:
                        if (
                            child.func.attr in {"__setattr__", "__delattr__"}
                            and isinstance(child.func.value, ast.Name)
                            and child.func.value.id == "object"
                        ):
                            continue
                        return False
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if child.func.id in {"setattr", "delattr"} and child.args:
                        target = child.args[0]
                        if isinstance(target, ast.Name) and target.id in {"self", "cls"}:
                            return False
                if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    targets: list[ast.AST] = []
                    if isinstance(child, ast.Assign):
                        targets.extend(child.targets)
                    else:
                        targets.append(child.target)
                    if any(
                        isinstance(target, (ast.Attribute, ast.Subscript))
                        and isinstance(getattr(target, "value", None), ast.Name)
                        and target.value.id in {"self", "cls"}
                        for target in targets
                    ):
                        return False
                if isinstance(child, ast.Delete) and any(
                    isinstance(target, (ast.Attribute, ast.Subscript))
                    and isinstance(getattr(target, "value", None), ast.Name)
                    and target.value.id in {"self", "cls"}
                    for target in child.targets
                ):
                    return False
    return True


def _annotation_for(
    module: str,
    name: str,
    *,
    node: ast.AST,
    lines: Sequence[str],
    dataclass: bool,
    frozen_dataclass: bool,
) -> Optional[str]:
    identity = module + "." + name
    if (
        identity in PURE_VALUE_EXPORT_ANNOTATIONS
        and frozen_dataclass
        and _structurally_immutable_class(node)
    ):
        return PURE_VALUE_EXPORT_ANNOTATIONS[identity]
    line_number = int(getattr(node, "lineno", 1))
    # Only a standalone preceding comment is an annotation.  Decorator names
    # and arbitrary text are not exemptions, and the class must still pass the
    # structural immutable-record check.
    for marker, label in (
        ("# production-audit: pure-value", "pure-value"),
        ("# production-audit: pure", "pure-value"),
    ):
        if (
            _has_marker(lines, line_number, marker)
            and frozen_dataclass
            and _structurally_immutable_class(node)
        ):
            return label
    if dataclass:
        return None
    return None


def _export_names(tree: ast.Module) -> Optional[set[str]]:
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in statement.targets):
            continue
        try:
            value = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError):
            return None
        if isinstance(value, (list, tuple, set)) and all(isinstance(item, str) for item in value):
            return set(value)
        return None
    return None


def _parse_modules(root: Path) -> tuple[_Module, ...]:
    automation = root / "automation"
    search_roots = [automation] if automation.is_dir() else [root]
    paths: list[Path] = []
    for search_root in search_roots:
        try:
            paths.extend(
                path
                for path in search_root.rglob("*.py")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not path.name.startswith("test_")
                and not path.name.endswith("_test.py")
                and path.name != "__init__.py"
            )
        except OSError as exc:
            raise ProductionAuditError("unable to enumerate automation Python files") from exc
    modules: list[_Module] = []
    for path in sorted(set(paths), key=lambda item: item.relative_to(root).as_posix()):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise ProductionAuditError(f"unable to parse production module: {path}") from exc
        module_name = _module_name(path, repo=root, automation=automation)
        lines = tuple(text.splitlines())
        export_names = _export_names(tree)
        definitions: dict[str, _Definition] = {}
        for statement in tree.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            decorators = tuple(_decorator_name(item) for item in getattr(statement, "decorator_list", ()))
            dataclass, frozen_dataclass = _dataclass_traits(statement, decorators)
            annotation = _annotation_for(
                module_name,
                statement.name,
                node=statement,
                lines=lines,
                dataclass=dataclass,
                frozen_dataclass=frozen_dataclass,
            )
            definitions[statement.name] = _Definition(
                module=module_name,
                name=statement.name,
                kind="class" if isinstance(statement, ast.ClassDef) else "function",
                node=statement,
                path=path,
                source_lines=lines,
                decorators=decorators,
                dataclass=dataclass,
                frozen_dataclass=frozen_dataclass,
                annotation=annotation,
            )
        if export_names is None:
            exported = tuple(
                item for name, item in sorted(definitions.items()) if not name.startswith("_")
            )
        else:
            exported = tuple(
                item
                for name, item in sorted(definitions.items())
                if name in export_names
            )
        from_imports: dict[str, tuple[str, str]] = {}
        module_imports: dict[str, str] = {}
        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom):
                base = statement.module or ""
                if statement.level:
                    parent = module_name.split(".")[:-statement.level]
                    base = ".".join(parent + ([base] if base else []))
                for alias in statement.names:
                    if alias.name == "*":
                        continue
                    from_imports[alias.asname or alias.name] = (base, alias.name)
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    local = alias.asname or alias.name.split(".")[0]
                    module_imports[local] = alias.name
        modules.append(
            _Module(
                name=module_name,
                path=path,
                tree=tree,
                source_lines=lines,
                exports=exported,
                definitions=definitions,
                from_imports=from_imports,
                module_imports=module_imports,
                roots=set(),
            )
        )
    return tuple(modules)


def _is_tranche_module(module: _Module) -> bool:
    if module.name in TRANCHE_MODULES:
        return True
    short = module.name.rsplit(".", 1)[-1]
    text = "\n".join(module.source_lines[:8])
    return short.startswith("search_") or "tranche" in short or "production-audit: tranche" in text


def _is_registration(decorators: Sequence[str]) -> bool:
    markers = {
        "tool",
        "command",
        "route",
        "register",
        "register_tool",
        "register_command",
        "expose",
        "entrypoint",
        "connector",
        "mcp",
    }
    return any(
        part.rsplit(".", 1)[-1].lower() in markers
        for part in decorators
        if part
    )


def _registered_mapping_roots(module: _Module) -> set[str]:
    """Return local callables named by concrete command/connector mappings."""

    roots: set[str] = set()
    for statement in module.tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        target_names = {
            target.id
            for target in statement.targets
            if isinstance(target, ast.Name)
        }
        if not any(
            name == "REGISTRY"
            or name.endswith("_REGISTRY")
            or name in {"COMMANDS", "TOOLS", "ROUTES", "COMMAND_MAP", "TOOL_MAP"}
            for name in target_names
        ):
            continue
        for node in ast.walk(statement.value):
            if isinstance(node, ast.Name) and node.id in module.definitions:
                roots.add(module.name + "." + node.id)
    return roots


def _mark_roots(modules: Sequence[_Module]) -> set[str]:
    roots: set[str] = set()
    for module in modules:
        roots.update(_registered_mapping_roots(module))
        short = module.name.rsplit(".", 1)[-1].lower()
        for definition in module.definitions.values():
            if _is_registration(definition.decorators):
                roots.add(definition.identity)
            if _has_marker(definition.source_lines, int(getattr(definition.node, "lineno", 1)), "production-audit: root"):
                roots.add(definition.identity)
            if short in {"cli", "server", "connector", "commands", "commands_client", "mcp"} and (
                definition.name in {
                    "main",
                    "entry",
                    "run",
                }
            ):
                roots.add(definition.identity)
        for statement in module.tree.body:
            if not isinstance(statement, ast.If):
                continue
            test = statement.test
            is_main_guard = (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
                and any(isinstance(item, ast.Constant) and item.value == "__main__" for item in test.comparators)
            )
            if not is_main_guard:
                continue
            for node in ast.walk(statement):
                if isinstance(node, ast.Call):
                    target = node.func.id if isinstance(node.func, ast.Name) else None
                    if target in module.definitions:
                        roots.add(module.name + "." + target)
    return roots


class _CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[ast.AST] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node.func)
        self.generic_visit(node)


def _definition_call_nodes(definition: _Definition) -> tuple[ast.AST, ...]:
    collector = _CallCollector()
    if isinstance(definition.node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for statement in definition.node.body:
            collector.visit(statement)
    return tuple(collector.calls)


def _resolve_attribute(
    node: ast.Attribute,
    *,
    module: _Module,
    definitions: Mapping[str, _Definition],
    all_definitions: Mapping[str, tuple[str, ...]],
) -> Optional[str]:
    if isinstance(node.value, ast.Name):
        alias = node.value.id
        imported_module = module.module_imports.get(alias)
        if imported_module:
            candidate = imported_module + "." + node.attr
            if candidate in definitions:
                return candidate
            # The imported module may be an alias to an automation module
            # whose definitions were indexed under the canonical name.
            for identity in all_definitions.get(node.attr, ()):
                if identity.startswith(imported_module + "."):
                    return identity
        imported = module.from_imports.get(alias)
        if imported:
            candidate = imported[0] + "." + imported[1]
            if candidate in definitions:
                return candidate
    return None


def _build_graph(
    modules: Sequence[_Module],
) -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    module_by_name = {module.name: module for module in modules}
    definitions: dict[str, _Definition] = {
        definition.identity: definition
        for module in modules
        for definition in module.definitions.values()
    }
    all_by_short_name: dict[str, tuple[str, ...]] = {}
    grouped: dict[str, list[str]] = {}
    for identity in definitions:
        grouped.setdefault(identity.rsplit(".", 1)[-1], []).append(identity)
    all_by_short_name = {
        name: tuple(sorted(values)) for name, values in grouped.items()
    }
    edges: dict[str, set[str]] = {identity: set() for identity in definitions}
    reverse: dict[str, set[str]] = {identity: set() for identity in definitions}
    roots = _mark_roots(modules)
    for module in modules:
        local_defs = module.definitions
        for definition in local_defs.values():
            caller = definition.identity
            for call in _definition_call_nodes(definition):
                target: Optional[str] = None
                if isinstance(call, ast.Name):
                    if call.id in local_defs:
                        target = module.name + "." + call.id
                    elif call.id in module.from_imports:
                        imported_module, imported_name = module.from_imports[call.id]
                        candidate = imported_module + "." + imported_name
                        if candidate in definitions:
                            target = candidate
                    elif len(all_by_short_name.get(call.id, ())) == 1:
                        target = all_by_short_name[call.id][0]
                elif isinstance(call, ast.Attribute):
                    target = _resolve_attribute(
                        call,
                        module=module,
                        definitions=definitions,
                        all_definitions=all_by_short_name,
                    )
                    if target is None and len(all_by_short_name.get(call.attr, ())) == 1:
                        target = all_by_short_name[call.attr][0]
                if target is None or target not in definitions or target == caller:
                    continue
                edges[caller].add(target)
                reverse[target].add(caller)
    roots.intersection_update(definitions)
    return edges, reverse, roots


def _literal_assignment(tree: ast.Module, name: str) -> Optional[ast.AST]:
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets: tuple[ast.AST, ...]
        if isinstance(statement, ast.Assign):
            targets = tuple(statement.targets)
            value = statement.value
        else:
            targets = (statement.target,)
            value = statement.value
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return value
    return None


def _literal_strings(value: Optional[ast.AST]) -> tuple[str, ...]:
    if value is None:
        return ()
    try:
        raw = ast.literal_eval(value)
    except (TypeError, ValueError, SyntaxError):
        return ()
    if isinstance(raw, (tuple, list, set)) and all(isinstance(item, str) for item in raw):
        # LANES is an ordered protocol value.  Preserve its declared order so
        # closure findings and their identities do not drift alphabetically.
        return tuple(dict.fromkeys(raw))
    return ()


def _lane_condition_values(test: ast.AST) -> set[str]:
    """Return lane literals from a comparison whose left side is ``lane``.

    A string appearing anywhere in ``_dispatch`` is not dispatch evidence.  It
    must participate in a comparison against the dispatcher argument, and the
    comparison must be statically visible to this audit.
    """

    values: set[str] = set()
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare):
            continue
        lane_left = isinstance(node.left, ast.Name) and node.left.id == "lane"
        lane_right = any(
            isinstance(item, ast.Name) and item.id == "lane"
            for item in node.comparators
        )
        if not lane_left and not lane_right:
            continue
        candidates: list[ast.AST] = list(node.comparators)
        if lane_right:
            candidates.append(node.left)
        for candidate in candidates:
            if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
                values.add(candidate.value)
            elif isinstance(candidate, (ast.Set, ast.Tuple, ast.List)):
                values.update(
                    item.value
                    for item in candidate.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
    return values


def _branch_has_local_result(branch: ast.If, module: _Module) -> bool:
    """Require a lane branch to return a call to a local concrete definition."""

    local_names = set(module.definitions).difference({"_dispatch"})
    for node in ast.walk(branch):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
            continue
        target = _call_target_name(node.value.func)
        if target in local_names:
            return True
    return False


def _dispatch_lanes(module: Optional[_Module], lanes: Sequence[str]) -> set[str]:
    if module is None:
        return set()
    dispatch = next(
        (
            statement
            for statement in module.tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "_dispatch"
        ),
        None,
    )
    if dispatch is None:
        return set()
    found: set[str] = set()
    lane_set = set(lanes)
    for node in ast.walk(dispatch):
        if not isinstance(node, ast.If):
            continue
        values = _lane_condition_values(node.test)
        if values and _branch_has_local_result(node, module):
            found.update(value for value in values if value in lane_set)
    return found


def _mapping_keys(module: Optional[_Module], name: str) -> set[str]:
    return set(_literal_mapping(module, name))


def _literal_mapping(module: Optional[_Module], name: str) -> dict[str, ast.AST]:
    """Return only statically keyed entries from one module-level mapping."""

    if module is None:
        return {}
    value = _literal_assignment(module.tree, name)
    if not isinstance(value, ast.Dict):
        return {}
    result: dict[str, ast.AST] = {}
    for key, item in zip(value.keys, value.values):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            result[key.value] = item
    return result


def _literal_string_sequence(value: Optional[ast.AST]) -> Optional[tuple[str, ...]]:
    """Evaluate a tuple/list of nonempty strings, refusing expressions."""

    if value is None:
        return None
    try:
        raw = ast.literal_eval(value)
    except (TypeError, ValueError, SyntaxError):
        return None
    if not isinstance(raw, (tuple, list)):
        return None
    if not all(isinstance(item, str) and item for item in raw):
        return None
    values = tuple(raw)
    if len(set(values)) != len(values):
        return None
    return values


def _call_target_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _definition_node(definition: Optional[_Definition | ast.AST]) -> Optional[ast.AST]:
    if definition is None:
        return None
    return definition.node if isinstance(definition, _Definition) else definition


def _definition_has_call(
    definition: Optional[_Definition | ast.AST],
    names: set[str],
) -> bool:
    node = _definition_node(definition)
    if node is None:
        return False
    return any(
        _call_target_name(item.func) in names
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
    )


def _definition_uses_name(
    definition: Optional[_Definition | ast.AST],
    name: str,
) -> bool:
    node = _definition_node(definition)
    if node is None:
        return False
    return any(
        isinstance(item, ast.Name) and item.id == name
        for item in ast.walk(node)
    )


def _definition_uses_attribute(
    definition: Optional[_Definition | ast.AST],
    name: str,
) -> bool:
    node = _definition_node(definition)
    if node is None:
        return False
    return any(
        isinstance(item, ast.Attribute) and item.attr == name
        for item in ast.walk(node)
    )


def _module_has_definition(module: Optional[_Module], names: set[str]) -> bool:
    return bool(module and names.intersection(module.definitions))


def _module_has_call(module: Optional[_Module], names: set[str]) -> bool:
    if module is None:
        return False
    return any(
        _call_target_name(node.func) in names
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
    )


def _module_uses_name(module: Optional[_Module], name: str) -> bool:
    if module is None:
        return False
    return any(
        isinstance(node, ast.Name) and node.id == name
        for node in ast.walk(module.tree)
    )


def _class_method(
    module: Optional[_Module],
    class_name: str,
    method_name: str,
) -> Optional[ast.AST]:
    if module is None:
        return None
    definition = module.definitions.get(class_name)
    if definition is None or not isinstance(definition.node, ast.ClassDef):
        return None
    return next(
        (
            statement
            for statement in definition.node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == method_name
        ),
        None,
    )


def _module_path_identity(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str) or not value.endswith(".py"):
        return None
    normalized = value.replace("\\", "/")
    if not normalized.startswith("automation/") or ".." in normalized.split("/"):
        return None
    return normalized[:-3].replace("/", ".")


def _literal_string_set(value: Optional[ast.AST]) -> set[str]:
    """Evaluate a closed string set, including ``frozenset({...})``."""

    if value is None:
        return set()
    candidate = value
    if (
        isinstance(candidate, ast.Call)
        and isinstance(candidate.func, ast.Name)
        and candidate.func.id in {"set", "frozenset"}
        and len(candidate.args) == 1
        and not candidate.keywords
    ):
        candidate = candidate.args[0]
    if not isinstance(candidate, (ast.Set, ast.Tuple, ast.List)):
        try:
            evaluated = ast.literal_eval(candidate)
        except (TypeError, ValueError, SyntaxError):
            return set()
        if isinstance(evaluated, (set, frozenset, tuple, list)):
            return {
                item for item in evaluated
                if isinstance(item, str)
            }
        return set()
    return {
        item.value
        for item in candidate.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


def _call_keyword_is_name(call: ast.Call, keyword: str, name: str) -> bool:
    return any(
        item.arg == keyword
        and isinstance(item.value, ast.Name)
        and item.value.id == name
        for item in call.keywords
    )


def _call_has_positional_name(call: ast.Call, name: str) -> bool:
    return any(
        isinstance(argument, ast.Name) and argument.id == name
        for argument in call.args
    )


def _assignment_names(statement: ast.AST) -> set[str]:
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AnnAssign):
        targets = (statement.target,)
    else:
        return set()
    return {
        item.id
        for target in targets
        for item in ast.walk(target)
        if isinstance(item, ast.Name)
    }


def _subscript_is_name(node: ast.AST, base: str, index: str) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id != base:
        return False
    slice_node = node.slice
    return isinstance(slice_node, ast.Name) and slice_node.id == index


def _indexed_provider_binding(
    modules: Mapping[str, _Module],
    lane: str,
) -> bool:
    """Prove the indexed provider registry binds this lane to one runtime."""

    indexed = modules.get("automation.search_indexed_lane")
    if indexed is None:
        return False
    declared = _literal_string_set(_literal_assignment(indexed.tree, "INDEXED_LANES"))
    if lane not in declared:
        return False
    production = indexed.definitions.get("production_indexed_adapters")
    binder = indexed.definitions.get("indexed_lane_adapter")
    if production is None or binder is None:
        return False
    loop_bound = False
    for node in ast.walk(production.node):
        if not isinstance(node, ast.For):
            continue
        target_names = {
            item.id for item in ast.walk(node.target) if isinstance(item, ast.Name)
        }
        iter_names = {
            item.id for item in ast.walk(node.iter) if isinstance(item, ast.Name)
        }
        if "lane" not in target_names or "INDEXED_LANES" not in iter_names:
            continue
        has_registry_assignment = any(
            isinstance(item, ast.Assign)
            and any(
                _subscript_is_name(target, "adapters", "lane")
                for target in item.targets
            )
            for item in ast.walk(node)
        )
        has_bound_call = any(
            isinstance(item, ast.Call)
            and _call_target_name(item.func) == "indexed_lane_adapter"
            and _call_keyword_is_name(item, "lane", "lane")
            for item in ast.walk(node)
        )
        if has_registry_assignment and has_bound_call:
            loop_bound = True
            break
    runtime_checks = (
        _definition_has_call(production, {"_validate_runtime_binding"})
        and _definition_has_call(production, {"load_indexed_runtime"})
        and _definition_has_call(production, {"load_target_index"})
    )
    returns_typed_mapping = (
        _definition_uses_name(production, "LaneAdapters")
        and _definition_uses_attribute(production, "from_mapping")
    )
    return bool(loop_bound and runtime_checks and returns_typed_mapping)


def _lane_slice(value: ast.AST, lane: str) -> bool:
    """Return whether a registry lookup uses this lane or its loop variable."""

    if isinstance(value, ast.Index):  # pragma: no cover - Python 3.8 shape
        value = value.value
    if isinstance(value, ast.Constant):
        return value.value == lane
    return isinstance(value, ast.Name) and value.id == "lane"


def _registry_lookup(node: ast.AST, registry_name: str, lane: str) -> bool:
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == registry_name
    ):
        return _lane_slice(node.slice, lane)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == registry_name
        and node.func.attr == "get"
        and node.args
    ):
        return _lane_slice(node.args[0], lane)
    return False


def _concrete_registry_entry(
    module: _Module,
    entry: ast.AST,
    modules: Mapping[str, _Module],
) -> bool:
    """Require a registry entry to name a known callable, not a placeholder."""

    if isinstance(entry, ast.Name):
        definition = module.definitions.get(entry.id)
        if definition is not None and definition.kind in {"function", "class"}:
            return True
        imported = module.from_imports.get(entry.id)
        if imported is not None:
            imported_module = modules.get(imported[0])
            return bool(
                imported_module is not None
                and imported[1] in imported_module.definitions
            )
        imported_name = module.module_imports.get(entry.id)
        return bool(imported_name and imported_name in modules)
    if isinstance(entry, ast.Attribute) and isinstance(entry.value, ast.Name):
        imported_module = modules.get(module.module_imports.get(entry.value.id, ""))
        return bool(imported_module and entry.attr in imported_module.definitions)
    if isinstance(entry, ast.Call):
        return _concrete_registry_entry(module, entry.func, modules)
    return False


def _provider_registry_binding(
    modules: Mapping[str, _Module],
    lane: str,
) -> bool:
    """Prove one concrete lane registry lookup, not a self-description."""

    for module in modules.values():
        for statement in module.tree.body:
            if isinstance(statement, ast.Assign):
                names = {
                    target.id
                    for target in statement.targets
                    if isinstance(target, ast.Name)
                }
                value = statement.value
            elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                names = {statement.target.id}
                value = statement.value
            else:
                continue
            registry_names = {
                name
                for name in names
                if name.upper() in {
                    "PROVIDER_REGISTRY",
                    "LANE_PROVIDER_REGISTRY",
                    "LANE_PROVIDERS",
                    "ADAPTER_REGISTRY",
                    "LANE_ADAPTER_REGISTRY",
                    "LANE_ADAPTERS",
                }
                or any(name.upper().endswith(suffix) for suffix in _PROVIDER_REGISTRY_SUFFIXES)
            }
            if not registry_names or not isinstance(value, ast.Dict):
                continue
            entries = {
                key.value: item
                for key, item in zip(value.keys, value.values)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            entry = entries.get(lane)
            if entry is None or not _concrete_registry_entry(module, entry, modules):
                continue
            # A module-level mapping is a declaration only. Require a
            # function body to select this lane from that exact mapping.
            if any(
                definition.kind == "function"
                and any(
                    _registry_lookup(node, registry_name, lane)
                    for node in ast.walk(definition.node)
                )
                for definition in module.definitions.values()
                for registry_name in registry_names
            ):
                return True
    return False


def _factory_surface(
    modules: Mapping[str, _Module],
    lane: str,
) -> tuple[bool, bool, bool]:
    """Return independent factory-module, tool, and input bindings."""

    factory = modules.get("automation.search_run_factory")
    create = factory.definitions.get("create_instrumented_run") if factory else None
    normalize = factory.definitions.get("_normalize_inputs") if factory else None
    module_ok = factory is not None and create is not None and normalize is not None
    factory_defs = (create, factory.definitions.get("_create_instrumented_run_locked") if factory else None)
    input_ok = (
        module_ok
        and any(_definition_has_call(item, {"_normalize_inputs"}) for item in factory_defs)
        and _definition_uses_name(normalize, "LANES")
        and _definition_uses_name(normalize, "lanes")
    )
    entries = _literal_mapping(factory, "_LANE_MODULES")
    raw_entry = entries.get(lane)
    paths = _literal_string_sequence(raw_entry)
    mapped_modules = (
        paths is not None
        and bool(paths)
        and all(
            (identity := _module_path_identity(path)) is not None
            and identity in modules
            for path in paths
        )
    )
    # Every lane must flow into the factory's immutable tool identity payload.
    # The five lanes with extra source modules additionally need their explicit
    # immutable module registry entry.  The remaining built-ins are bound by
    # the canonical selected-lanes tuple passed to ``_tool_identities``.
    tool_identity_ok = any(
        _definition_has_call(item, {"_tool_identities"})
        and _definition_uses_name(item, "selected_lanes")
        for item in factory_defs
    )
    if lane in _CORE_FACTORY_LANES:
        lane_binding_ok = tool_identity_ok
    else:
        lane_binding_ok = (
            tool_identity_ok
            and mapped_modules
            and _module_uses_name(factory, "_LANE_MODULES")
        )
    tool_ok = module_ok and input_ok and lane_binding_ok
    return (not module_ok, not tool_ok, not input_ok)


def _direct_dispatch_provider_binding(
    module: Optional[_Module],
    lane: str,
) -> bool:
    """Accept only a known concrete built-in provider branch."""

    if module is None:
        return False
    dispatch = next(
        (
            statement
            for statement in module.tree.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "_dispatch"
        ),
        None,
    )
    if dispatch is None:
        return False
    for branch in ast.walk(dispatch):
        if not isinstance(branch, ast.If) or lane not in _lane_condition_values(branch.test):
            continue
        for node in ast.walk(branch):
            if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
                continue
            target = _call_target_name(node.value.func)
            if target in _DIRECT_DISPATCH_PROVIDER_NAMES and target in module.definitions:
                return True
    return False


def _provider_surface(
    modules: Mapping[str, _Module],
    lane: str,
    *,
    factory_bound: bool = True,
) -> tuple[bool, bool, bool]:
    """Return independent immutable-provider, adaptor-field, and input checks."""

    lanes_module = modules.get("automation.search_lanes")
    adapters = lanes_module.definitions.get("LaneAdapters") if lanes_module else None
    module_ok = (
        adapters is not None
        and adapters.dataclass
        and adapters.frozen_dataclass
        and _structurally_immutable_class(adapters.node)
    )
    fields = _dataclass_fields(lanes_module, "LaneAdapters")
    adaptor_ok = lane in fields
    method = _class_method(lanes_module, "LaneAdapters", "from_mapping")
    typed_input = method is not None and any(
        isinstance(node, ast.Name) and node.id == "Mapping"
        for node in ast.walk(method)
    ) and any(
        isinstance(node, ast.Call)
        and _call_target_name(node.func) == "callable"
        for node in ast.walk(method)
    ) and _definition_has_call(method, {"fields"})
    direct_binding = _direct_dispatch_provider_binding(lanes_module, lane)
    lane_binding = (
        direct_binding
        or _indexed_provider_binding(modules, lane)
        or _provider_registry_binding(modules, lane)
    )
    # A dataclass field and a dispatch branch are independent facts. The
    # provider input is closed only when a concrete provider is also admitted
    # through the factory's lane-bound tool evidence.
    input_ok = bool(typed_input and lane_binding and factory_bound)
    return (not module_ok, not adaptor_ok, not input_ok)


def _call_references_name(call: ast.Call, names: set[str]) -> bool:
    """Return whether a call carries one of the required typed inputs."""

    return any(
        isinstance(node, ast.Name) and node.id in names
        for node in ast.walk(call)
    )


def _supervisor_adapter_reconstruction(
    module: _Module,
) -> bool:
    """Require supervisor adapter construction from manifest-bound runtime data."""

    entry = module.definitions.get("_run_instrumented_entry")
    locked = module.definitions.get("_run_instrumented_locked")
    for definition in (entry, locked):
        if definition is None:
            continue
        for node in ast.walk(definition.node):
            if not isinstance(node, ast.Call):
                continue
            target = _call_target_name(node.func)
            if target not in _RUNTIME_ADAPTER_FACTORY_NAMES:
                continue
            if not _call_references_name(node, {"manifest"}):
                continue
            if not _call_references_name(node, {"runtime", "run_archive", "archive", "runtime_id"}):
                continue
            return True
    return False


def _supervisor_lane_reconstruction(
    module: Optional[_Module],
    lane: Optional[str] = None,
    *,
    require_provider_chain: bool = False,
) -> bool:
    """Prove typed task execution and, when needed, provider reconstruction."""

    del lane
    if module is None:
        return False
    locked = module.definitions.get("_run_instrumented_locked")
    entry = module.definitions.get("_run_instrumented_entry")
    wrappers = (
        module.definitions.get("run_instrumented"),
        module.definitions.get("resume_instrumented"),
    )
    if locked is None or entry is None or any(item is None for item in wrappers):
        return False
    lane_loop = False
    for node in ast.walk(locked.node):
        if not isinstance(node, ast.For):
            continue
        target_names = {
            item.id for item in ast.walk(node.target) if isinstance(item, ast.Name)
        }
        iter_names = {
            item.id for item in ast.walk(node.iter) if isinstance(item, ast.Name)
        }
        if "lane" not in target_names or "lanes" not in iter_names:
            continue
        task_names: set[str] = set()
        started_names: set[str] = set()
        for item in ast.walk(node):
            if not isinstance(item, (ast.Assign, ast.AnnAssign)):
                continue
            value = item.value
            if not isinstance(value, ast.Call):
                continue
            target = _call_target_name(value.func)
            names = _assignment_names(item)
            if target == "create_task" and _call_keyword_is_name(value, "lane", "lane"):
                task_names.update(names)
            if target == "start_task":
                started_names.update(names)
        creates_lane_task = any(
            isinstance(item, ast.Call)
            and _call_target_name(item.func) == "create_task"
            and _call_keyword_is_name(item, "lane", "lane")
            for item in ast.walk(node)
        )
        executes_with_adapters = any(
            isinstance(item, ast.Call)
            and _call_target_name(item.func) == "lane_executor"
            and any(
                keyword.arg == "adapters"
                and isinstance(keyword.value, ast.Name)
                and keyword.value.id == "adapters"
                for keyword in item.keywords
            )
            and (
                _call_keyword_is_name(item, "lane", "lane")
                or _call_has_positional_name(item, "lane")
                or bool(task_names.intersection({
                    argument.id
                    for argument in item.args
                    if isinstance(argument, ast.Name)
                }))
                or bool(started_names.intersection({
                    argument.id
                    for argument in item.args
                    if isinstance(argument, ast.Name)
                }))
            )
            for item in ast.walk(node)
        )
        if creates_lane_task and executes_with_adapters:
            lane_loop = True
            break
    entry_ok = (
        _definition_has_call(entry, {"_load_manifest", "_load_manifest_file"})
        and _definition_has_call(entry, {"verify_factory_runtime"})
        and _definition_has_call(entry, {"_run_instrumented_locked"})
        and _definition_has_call(entry, {"_ordered_lanes"})
        and _definition_uses_name(entry, "manifest")
    )
    wrappers_ok = all(
        _definition_has_call(item, {"_run_instrumented_entry"})
        for item in wrappers
    )
    if not (lane_loop and entry_ok and wrappers_ok):
        return False
    if require_provider_chain and not _supervisor_adapter_reconstruction(module):
        return False
    return True


def _attribute_on_name(definition: _Definition, base: str, attribute: str) -> bool:
    return any(
        isinstance(node, ast.Attribute)
        and node.attr == attribute
        and isinstance(node.value, ast.Name)
        and node.value.id == base
        for node in ast.walk(definition.node)
    )


def _is_event_branch(test: ast.AST, event_type: str) -> bool:
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare):
            continue
        if not (
            isinstance(node.left, ast.Attribute)
            and node.left.attr == "event_type"
            and isinstance(node.left.value, ast.Name)
            and node.left.value.id == "event"
        ):
            continue
        if any(
            isinstance(item, ast.Constant) and item.value == event_type
            for item in node.comparators
        ):
            return True
    return False


def _recovery_provider_revalidation(recover: _Definition) -> bool:
    """Require a runtime/provider identity verifier on the recovery path."""

    has_verifier = _definition_has_call(recover, _RUNTIME_REVALIDATION_NAMES)
    lane_identity = (
        _attribute_on_name(recover, "manifest", "tool_identities")
        and _attribute_on_name(recover, "receipt", "tool_identities")
        and _definition_uses_name(recover, "LANE_TOOL_KEYS")
    )
    return bool(has_verifier and lane_identity)


def _recovery_lane_reconstruction(
    module: Optional[_Module],
    lane: Optional[str] = None,
    *,
    require_provider_chain: bool = False,
) -> bool:
    """Require recovery to revalidate manifest-bound lane provider identity."""

    del lane
    if module is None:
        return False
    recover = module.definitions.get("recover_run")
    if recover is None:
        return False
    event_branch = False
    for node in ast.walk(recover.node):
        if not isinstance(node, ast.If) or not _is_event_branch(node.test, "exhaustion_recorded"):
            continue
        event_branch = (
            _attribute_on_name(recover, "receipt", "lane")
            and _attribute_on_name(recover, "manifest", "selected_lanes")
            and _attribute_on_name(recover, "receipt", "tool_identities")
            and _attribute_on_name(recover, "manifest", "tool_identities")
        )
        if event_branch:
            break
    generic_replay = (
        _definition_has_call(recover, {"_load_manifest"})
        and _definition_has_call(recover, {"validate_ledger_prefix"})
        and _definition_has_call(recover, {"frontier_from_events"})
        and _definition_uses_name(recover, "LANE_TOOL_KEYS")
    )
    if not (event_branch and generic_replay):
        return False
    if require_provider_chain and not _recovery_provider_revalidation(recover):
        return False
    return True


def _runtime_surface(
    modules: Mapping[str, _Module],
    lane: str,
    *,
    dispatched: bool,
    provider_bound: bool,
    require_provider_chain: bool = False,
) -> tuple[bool, bool]:
    """Check supervisor and recovery reconstruction as separate surfaces."""

    supervisor = modules.get("automation.search_supervisor")
    recovery = modules.get("automation.search_recovery")
    supervisor_surface = (
        dispatched
        and provider_bound
        and _supervisor_lane_reconstruction(
            supervisor,
            lane,
            require_provider_chain=require_provider_chain,
        )
    )
    recovery_surface = (
        dispatched
        and provider_bound
        and _recovery_lane_reconstruction(
            recovery,
            lane,
            require_provider_chain=require_provider_chain,
        )
    )
    return (not supervisor_surface, not recovery_surface)


def _cli_lane_surface(module: Optional[_Module], lane: str) -> bool:
    """Prove parser, normalization, and dispatch are wired by AST facts."""

    if module is None or not _module_has_definition(module, {"build_parser", "_normalize_lanes", "_dispatch"}):
        return False
    parser = module.definitions.get("build_parser")
    normalize = module.definitions.get("_normalize_lanes")
    dispatch = module.definitions.get("_dispatch")
    has_lanes_option = any(
        isinstance(node, ast.Call)
        and _call_target_name(node.func) == "add_argument"
        and any(
            isinstance(argument, ast.Constant) and argument.value == "--lanes"
            for argument in node.args
        )
        for node in ast.walk(parser.node if parser else ast.Pass())
    )
    normalizes = (
        _definition_has_call(normalize, {"validate_lane"})
        and _definition_uses_name(normalize, "LANES")
    )
    dispatches = (
        _definition_has_call(dispatch, {"plan_selection", "create_instrumented_run"})
        and _definition_uses_attribute(dispatch, "lanes")
    )
    return bool(has_lanes_option and normalizes and dispatches and lane)


def _connector_lane_surface(module: Optional[_Module], lane: str) -> bool:
    """Prove typed lane validation reaches the concrete connector registry."""

    if module is None:
        return False
    declared = _literal_strings(_literal_assignment(module.tree, "_SEARCH_LANES"))
    if lane not in declared:
        return False
    validator = module.definitions.get("_search_lanes")
    create_argv = module.definitions.get("_search_create_argv")
    registry = _literal_mapping(module, "REGISTRY")
    registered = registry.get("search_create_instrumented")
    if validator is None or create_argv is None or registered is None:
        return False
    validator_ok = (
        _definition_has_call(validator, {"set", "tuple"})
        and _definition_has_call(validator, {"difference"})
        and _definition_uses_name(validator, "_SEARCH_LANES")
    )
    create_ok = (
        _definition_has_call(create_argv, {"_search_component", "_search_record_ids", "_search_lanes"})
    )
    registration_ok = any(
        isinstance(node, ast.Call)
        and _call_target_name(node.func) == "_search_create_argv"
        for node in ast.walk(registered)
    )
    return bool(validator_ok and create_ok and registration_ok)


def _dataclass_fields(module: Optional[_Module], name: str) -> set[str]:
    if module is None:
        return set()
    definition = module.definitions.get(name)
    if definition is None or not isinstance(definition.node, ast.ClassDef):
        return set()
    return {
        statement.target.id
        for statement in definition.node.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
    }


def _audit_lane_closure(modules: Sequence[_Module]) -> tuple[LaneClosureFinding, ...]:
    """Find advertised lanes with no executable production path.

    Every surface is checked independently.  A dispatcher branch therefore
    cannot hide a missing factory binding, provider input, recovery path, CLI
    selection, or typed connector registration.
    """

    by_name = {module.name: module for module in modules}
    types_module = by_name.get("automation.search_types")
    lanes = _literal_strings(_literal_assignment(types_module.tree, "LANES")) if types_module else ()
    if not lanes:
        return ()
    dispatch = _dispatch_lanes(by_name.get("automation.search_lanes"), lanes)
    cli_module = by_name.get("automation.search_cli")
    connector = by_name.get("automation.mcp.commands_client")
    findings: list[LaneClosureFinding] = []
    for lane in lanes:
        missing_dispatcher = lane not in dispatch
        missing_factory_module, missing_factory_tool, missing_factory_input = _factory_surface(
            by_name, lane
        )
        missing_factory = (
            missing_factory_module
            or missing_factory_tool
            or missing_factory_input
        )
        missing_provider_module, missing_provider_adaptor, missing_provider_input = _provider_surface(
            by_name,
            lane,
            factory_bound=not missing_factory,
        )
        missing_provider = (
            missing_provider_module
            or missing_provider_adaptor
            or missing_provider_input
        )
        # A registry-backed provider must be reconstructed from the manifest
        # runtime and revalidated during recovery.  Built-in discovery branches
        # are already concrete and retain the historical direct path.
        requires_provider_chain = _provider_registry_binding(by_name, lane)
        missing_supervisor, missing_recovery = _runtime_surface(
            by_name,
            lane,
            dispatched=not missing_dispatcher,
            provider_bound=not missing_provider,
            require_provider_chain=requires_provider_chain,
        )
        cli_reachable = _cli_lane_surface(cli_module, lane)
        connector_reachable = _connector_lane_surface(connector, lane)
        missing_cli_connector = not (cli_reachable and connector_reachable)
        categories = tuple(
            name
            for name, missing in (
                ("dispatcher", missing_dispatcher),
                ("factory_tool_binding", missing_factory),
                ("provider_input", missing_provider),
                ("supervisor_reachability", missing_supervisor),
                ("recovery_reachability", missing_recovery),
                ("cli_reachability", not cli_reachable),
                ("connector_reachability", not connector_reachable),
            )
            if missing
        )
        if categories:
            findings.append(
                LaneClosureFinding(
                    lane=lane,
                    missing_dispatcher=missing_dispatcher,
                    missing_factory_tool_binding=missing_factory,
                    missing_provider_input=missing_provider,
                    missing_cli_connector_reachability=missing_cli_connector,
                    categories=categories,
                    cli_reachable=cli_reachable,
                    connector_reachable=connector_reachable,
                    missing_supervisor_reachability=missing_supervisor,
                    missing_recovery_reachability=missing_recovery,
                    missing_factory_module=missing_factory_module,
                    missing_factory_tool=missing_factory_tool,
                    missing_factory_input=missing_factory_input,
                    missing_provider_module=missing_provider_module,
                    missing_provider_adaptor=missing_provider_adaptor,
                )
            )
    return tuple(sorted(findings, key=lambda item: lanes.index(item.lane)))


def _caller_chains(
    edges: Mapping[str, set[str]],
    roots: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    chains: dict[str, tuple[str, ...]] = {}
    queue: deque[tuple[str, tuple[str, ...]]] = deque(
        (root, (root,)) for root in sorted(set(roots))
    )
    while queue:
        current, chain = queue.popleft()
        previous = chains.get(current)
        if previous is not None and len(previous) <= len(chain):
            continue
        chains[current] = chain
        for target in sorted(edges.get(current, ())):
            queue.append((target, chain + (target,)))
    return chains


def _report_identity(
    exports: Sequence[ProductionExport],
    unreachable: Sequence[str],
    annotation_errors: Sequence[str],
    chains: Mapping[str, Sequence[str]],
    roots: Sequence[str],
    lane_findings: Sequence[LaneClosureFinding],
) -> str:
    payload = {
        "protocol": PRODUCTION_AUDIT_PROTOCOL,
        "exports": [item.to_dict() for item in exports],
        "unreachable_exports": list(unreachable),
        "annotation_errors": list(annotation_errors),
        "caller_chains": {key: list(value) for key, value in sorted(chains.items())},
        "production_roots": list(roots),
        "lane_findings": [item.to_dict() for item in lane_findings],
    }
    return hash_canonical(payload)


def audit_production_exports(repo: Path | str) -> ProductionAuditReport:
    """Return a deterministic closure report for the production tranche."""

    root = _as_repo(repo)
    modules = _parse_modules(root)
    tranche_modules = tuple(module for module in modules if _is_tranche_module(module))
    edges, reverse, roots = _build_graph(modules)
    chains = _caller_chains(edges, sorted(roots))
    exports: list[ProductionExport] = []
    unreachable: list[str] = []
    annotation_errors: list[str] = []
    for module in tranche_modules:
        for definition in module.exports:
            identity = definition.identity
            if definition.dataclass and definition.annotation is None:
                annotation_errors.append(identity)
                classification = "unannotated_value"
            elif definition.annotation is not None:
                classification = "pure_value"
            else:
                classification = "production"
            chain = tuple(chains.get(identity, ()))
            if classification == "production" and not chain:
                unreachable.append(identity)
            exports.append(
                ProductionExport(
                    identity=identity,
                    module=definition.module,
                    name=definition.name,
                    kind=definition.kind,
                    classification=classification,
                    annotation=definition.annotation,
                    callers=tuple(sorted(reverse.get(identity, set()))),
                    caller_chain=chain,
                )
            )
    exports.sort(key=lambda item: item.identity)
    unreachable = sorted(set(unreachable))
    annotation_errors = sorted(set(annotation_errors))
    lane_findings = _audit_lane_closure(modules)
    lane_closure_errors = tuple(item.lane for item in lane_findings)
    frozen_chains = {
        item.identity: tuple(item.caller_chain)
        for item in exports
        if item.caller_chain
    }
    ordered_roots = tuple(sorted(roots))
    identity = _report_identity(
        exports,
        unreachable,
        annotation_errors,
        frozen_chains,
        ordered_roots,
        lane_findings,
    )
    return ProductionAuditReport(
        exports=tuple(exports),
        unreachable_exports=tuple(unreachable),
        annotation_errors=tuple(annotation_errors),
        caller_chains=frozen_chains,
        production_roots=ordered_roots,
        identity=identity,
        lane_findings=lane_findings,
        lane_closure_errors=lane_closure_errors,
    )


__all__ = [
    "PRODUCTION_AUDIT_PROTOCOL",
    "PURE_VALUE_EXPORTS",
    "PURE_VALUE_EXPORT_ANNOTATIONS",
    "PURE_VALUE_ANNOTATIONS",
    "TRANCHE_MODULES",
    "EXPECTED_LANE_CLOSURE_GAPS",
    "LaneClosureFinding",
    "ProductionAuditError",
    "ProductionAuditReport",
    "ProductionExport",
    "audit_production_exports",
]
