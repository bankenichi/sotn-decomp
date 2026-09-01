"""Read-only lane adapters backed by the immutable donor query index.

The indexed lane is the boundary between the archive-verified donor query and
the ordinary lane discovery normalizer.  A query is bound once when the
adapter is created.  Per-recipient callbacks then create one typed query,
render only semantic claims, and return ordinary discovery values carrying
the complete immutable query provenance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # package imports
    from .search_archive import ArtifactRef, ContentAddressedArchive
    from .search_donor_index import DonorIndexBinding, DonorIndexGeneration
    from .search_donor_query import (
        DonorQuery,
        DonorQueryResult,
        DonorSemanticClaim,
        bind_donor_query,
    )
    from .search_lanes import (
        CandidateIdentityMismatch,
        LaneCandidate,
        LaneAdapters,
        LaneError,
        Recipient,
        SubsetViolation,
    )
    from .search_types import (
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_run_id,
    )
except ImportError:  # direct invocation from the automation directory
    from search_archive import ArtifactRef, ContentAddressedArchive  # type: ignore
    from search_donor_index import DonorIndexBinding, DonorIndexGeneration  # type: ignore
    from search_donor_query import (  # type: ignore
        DonorQuery,
        DonorQueryResult,
        DonorSemanticClaim,
        bind_donor_query,
    )
    from search_lanes import (  # type: ignore
        CandidateIdentityMismatch,
        LaneCandidate,
        LaneAdapters,
        LaneError,
        Recipient,
        SubsetViolation,
    )
    from search_types import (  # type: ignore
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_run_id,
    )


INDEXED_LANES = frozenset({"multi_donor", "cfg_dataflow"})
_RUNTIME_MANIFEST_KEYS = (
    "indexed_runtime",
    "indexed_runtime_id",
    "indexed_runtime_generation",
    "indexed_runtime_generation_id",
    "runtime_id",
)
_RENDERER_SOURCE_MANIFEST_KEY = "search_target_renderer"
_FORBIDDEN_RUNTIME_SUBSTITUTIONS = frozenset(
    {
        "query",
        "query_for",
        "render",
        "render_target",
        "render_target_context",
        "target_renderer",
        "scanner",
        "scan",
        "scan_revision",
        "provider",
        "callback",
        "callbacks",
        "repo",
        "repo_root",
        "source_root",
        "target_index",
        "target_context",
        "target_assembly",
        "target_bytes",
        "live_path",
        "run_archive",
        "runtime_archive",
        "index_archive",
        "integration_archive",
        "gate_archive",
        "archive",
        "artifact_root",
        "runtime_root",
        "runtime_path",
        "generation_path",
        "target_archive",
        "target_index_path",
        "queue",
        "queue_reader",
    }
)
_REFUSAL_CODES = {
    "empty": "donor_query_empty",
    "incompatible": "donor_query_incompatible",
    "ambiguous": "donor_query_ambiguous",
    "stale": "donor_query_stale",
}


def _revision_identity(revision: Any) -> str:
    try:
        return hash_canonical(revision.to_dict())
    except (AttributeError, TypeError, ValueError) as exc:
        raise LaneError("indexed query hit has an invalid pinned revision") from exc


def _artifact_identity(artifact: ArtifactRef) -> str:
    return hash_canonical(artifact.to_dict())


def _validate_result_provenance(
    result: DonorQueryResult,
    *,
    index: DonorIndexGeneration,
    query: DonorQuery,
    recipient: Recipient,
) -> None:
    """Check the result boundary before any target renderer is called."""

    if result.query != query:
        raise LaneError("indexed query result differs from the query callback value")
    if result.query.recipient_id != recipient.recipient_id:
        raise SubsetViolation("indexed query result recipient differs from selected recipient")
    if result.generation_id != index.generation_id:
        raise LaneError("indexed query result generation differs from bound index")
    artifact = result.provenance_artifact
    if not isinstance(artifact, ArtifactRef) or artifact != index.artifact:
        raise LaneError("indexed query result artifact metadata differs from bound index")
    try:
        validate_hash(artifact.content_hash, "indexed query artifact identity")
    except ValueError as exc:
        raise LaneError("indexed query result artifact identity is invalid") from exc
    if artifact.content_hash != result.generation_id:
        raise LaneError("indexed query result artifact is not bound to its generation")


def _rendered_candidates(
    rendered: Any,
    *,
    lane: str,
    recipient: Recipient,
) -> tuple[LaneCandidate, ...]:
    """Normalize and preflight typed renderer values.

    The ordinary lane normalizer performs the same candidate identity checks
    again.  Keeping this preflight here makes a direct adapter invocation obey
    the same recipient, lane, source, and artifact contract before its mapping
    is accepted by a lane.
    """

    if isinstance(rendered, LaneCandidate):
        values = (rendered,)
    elif isinstance(rendered, (list, tuple)):
        values = tuple(rendered)
    else:
        raise LaneError(
            "indexed target renderer must return a LaneCandidate or a sequence of LaneCandidate values"
        )
    for candidate in values:
        if not isinstance(candidate, LaneCandidate):
            raise LaneError("indexed target renderer returned an untyped candidate")
        if candidate.recipient_id != recipient.recipient_id:
            raise SubsetViolation("indexed target candidate recipient differs from selected recipient")
        if candidate.candidate.lane != lane:
            raise LaneError("indexed target candidate lane differs from adapter lane")
        artifact = candidate.candidate.source_artifact
        if not isinstance(artifact, ArtifactRef):
            raise CandidateIdentityMismatch("indexed target candidate has an invalid source artifact")
        if artifact.content_hash != candidate.candidate_id:
            raise CandidateIdentityMismatch(
                "indexed target candidate source artifact identity differs from candidate"
            )
        if not isinstance(candidate.source, str) or not candidate.source:
            raise CandidateIdentityMismatch(
                "indexed target renderer must return the candidate source text"
            )
        expected_path = (
            "artifacts/sources/"
            + candidate.candidate_id.removeprefix("sha256:")
            + ".c"
        )
        if (
            artifact.path != expected_path
            or artifact.media_type != "text/x-c"
            or isinstance(artifact.byte_size, bool)
            or not isinstance(artifact.byte_size, int)
        ):
            raise CandidateIdentityMismatch(
                "indexed target candidate source artifact metadata is not canonical"
            )
        source_bytes = candidate.source.encode("utf-8")
        if hash_bytes(source_bytes) != candidate.candidate_id:
            raise CandidateIdentityMismatch(
                "indexed target candidate source identity differs from candidate"
            )
        if artifact.byte_size != len(source_bytes):
            raise CandidateIdentityMismatch(
                "indexed target candidate source artifact metadata differs from source"
            )
    return values


def _provenance(
    result: DonorQueryResult,
    *,
    lane: str,
    recipient: Recipient,
) -> tuple[dict[str, Any], ...]:
    """Encode the query result's immutable identities as lane provenance."""

    artifact = result.provenance_artifact
    artifact_dict = artifact.to_dict()
    artifact_identity = _artifact_identity(artifact)
    entry_ids = tuple(hit.entry.entry_id for hit in result.hits)
    revision_identities = tuple(
        _revision_identity(hit.entry.revision) for hit in result.hits
    )
    claim_identities = tuple(sorted({hit.claim_identity for hit in result.hits}))
    summary: dict[str, Any] = {
        "kind": "indexed_donor_query",
        "lane": lane,
        "recipient_id": recipient.recipient_id,
        "source": artifact.path,
        "source_identity": artifact.content_hash,
        "input_identity": result.query_identity,
        "query_identity": result.query_identity,
        "status": result.status,
        "claim_identities": list(claim_identities),
        "entry_ids": list(entry_ids),
        "revision_identities": list(revision_identities),
        "generation_id": result.generation_id,
        "artifact": artifact_dict,
        "provenance_artifact": artifact_dict,
        "artifact_identity": artifact_identity,
        "receipt": None if result.receipt is None else result.receipt.to_dict(),
    }
    entries = [summary]
    for hit, revision_identity in zip(result.hits, revision_identities):
        entries.append(
            {
                "kind": "indexed_donor_hit",
                "lane": lane,
                "recipient_id": recipient.recipient_id,
                "source": artifact.path,
                "source_identity": artifact.content_hash,
                "input_identity": hit.entry.entry_id,
                "query_identity": result.query_identity,
                "entry_id": hit.entry.entry_id,
                "claim_identity": hit.claim_identity,
                "revision_identity": revision_identity,
                "revision": hit.entry.revision.revision,
                "generation_id": result.generation_id,
                "artifact": artifact_dict,
                "provenance_artifact": artifact_dict,
                "artifact_identity": artifact_identity,
                "status": result.status,
            }
        )
    return tuple(entries)


def _input_identities(result: DonorQueryResult) -> tuple[str, ...]:
    identities = [
        result.query_identity,
        result.generation_id,
        _artifact_identity(result.provenance_artifact),
    ]
    identities.extend(sorted({hit.claim_identity for hit in result.hits}))
    for hit in result.hits:
        identities.append(hit.entry.entry_id)
        identities.append(_revision_identity(hit.entry.revision))
    if result.receipt is not None:
        identities.append(result.receipt.receipt_id)
    return tuple(dict.fromkeys(identities))


def _semantic_claims(result: DonorQueryResult) -> tuple[DonorSemanticClaim, ...]:
    """Return one deterministic renderer claim for each semantic identity."""

    return result.semantic_claims


@dataclass(frozen=True)
class _TargetContextRenderer:
    """Render target context with the query that selected the claims.

    The indexed adapter invokes the donor query and target renderer as two
    separate callbacks.  Keeping the handoff as an immutable value avoids a
    process-local ``recipient_id -> query`` cache, while still making the
    renderer consume the exact query whose result it is rendering.  The
    two-argument ``__call__`` remains available for callers that use this
    object directly; the adapter uses ``render_with_query`` so a matched
    retry never needs a second target-query derivation.
    """

    manifest: RunManifest
    target_index: Any
    lane: str

    def __call__(
        self,
        recipient: Recipient,
        claims: tuple[DonorSemanticClaim, ...],
    ) -> Any:
        try:
            from .search_target_renderer import query_for_recipient
        except ImportError:  # direct invocation from the automation directory
            from search_target_renderer import query_for_recipient  # type: ignore

        query = query_for_recipient(self.manifest, self.target_index, recipient)
        return self.render_with_query(recipient, claims, query)

    def render_with_query(
        self,
        recipient: Recipient,
        claims: tuple[DonorSemanticClaim, ...],
        query: DonorQuery,
    ) -> Any:
        try:
            from .search_target_renderer import render_target_candidate
        except ImportError:  # direct invocation from the automation directory
            from search_target_renderer import render_target_candidate  # type: ignore

        return render_target_candidate(
            self.manifest,
            self.target_index,
            recipient,
            claims,
            lane=self.lane,
            query=query,
        )


def indexed_lane_adapter(
    index: DonorIndexGeneration,
    *,
    lane: str,
    expected_binding: DonorIndexBinding,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
    query_for: Callable[[Recipient], DonorQuery],
    render_target_context: Callable[
        [Recipient, tuple[DonorSemanticClaim, ...]],
        Any,
    ],
) -> Callable[[Recipient], Mapping[str, Any]]:
    """Bind one archive-verified donor index to an ordinary read-only lane."""

    if lane not in INDEXED_LANES:
        raise LaneError("indexed lane adapter supports only multi_donor or cfg_dataflow")
    if not callable(query_for):
        raise LaneError("indexed lane adapter query_for must be callable")
    if not callable(render_target_context):
        raise LaneError("indexed lane adapter renderer must be callable")

    # This performs the archive and integration-gate verification exactly once
    # for the lifetime of the adapter.  Callback invocations consume only the
    # resulting pure query closure.
    bound_query = bind_donor_query(
        index,
        expected_binding=expected_binding,
        index_archive=index_archive,
        integration_archive=integration_archive,
    )

    def callback(recipient: Recipient) -> Mapping[str, Any]:
        if not isinstance(recipient, Recipient):
            raise LaneError("indexed lane callback requires a typed Recipient")
        query = query_for(recipient)
        if not isinstance(query, DonorQuery):
            raise LaneError("indexed lane query_for must return a typed DonorQuery")
        result = bound_query(query)
        if not isinstance(result, DonorQueryResult):
            raise LaneError("indexed donor binder must return a typed DonorQueryResult")
        _validate_result_provenance(
            result,
            index=index,
            query=query,
            recipient=recipient,
        )
        provenance = _provenance(result, lane=lane, recipient=recipient)
        identities = _input_identities(result)

        if result.status != "matched":
            if result.status not in _REFUSAL_CODES:
                raise LaneError("indexed donor query returned an unsupported status")
            completion_reason = (
                "inapplicable"
                if result.status == "stale"
                else "search_space_exhausted"
            )
            return {
                "candidates": (),
                "attempts": 1,
                "input_identities": identities,
                "provenance": provenance,
                "completion_reason": completion_reason,
                "refusal_code": _REFUSAL_CODES[result.status],
                "reason": f"indexed donor query returned {result.status}",
            }

        claims = _semantic_claims(result)
        if isinstance(render_target_context, _TargetContextRenderer):
            rendered = render_target_context.render_with_query(
                recipient,
                claims,
                query,
            )
        else:
            rendered = render_target_context(recipient, claims)
        # A target translation failure is a successful, typed lane refusal,
        # not an empty search.  Import locally to keep this adapter usable as
        # the renderer's dependency without creating an import cycle.
        try:
            from .search_target_renderer import TargetContextUnsupported
        except ImportError:  # direct invocation from the automation directory
            from search_target_renderer import TargetContextUnsupported  # type: ignore

        if isinstance(rendered, TargetContextUnsupported):
            if rendered.recipient_id != recipient.recipient_id:
                raise SubsetViolation(
                    "indexed target refusal recipient differs from selected recipient"
                )
            if rendered.query != query:
                raise LaneError(
                    "indexed target refusal query differs from indexed donor query"
                )
            target_provenance: list[dict[str, Any]] = []
            for edge in rendered.provenance:
                normalized = dict(edge)
                if normalized.get("lane") not in (None, lane):
                    raise LaneError(
                        "indexed target refusal provenance lane differs from adapter lane"
                    )
                if normalized.get("recipient_id") not in (
                    None,
                    recipient.recipient_id,
                ):
                    raise SubsetViolation(
                        "indexed target refusal provenance recipient differs from selected recipient"
                    )
                normalized["lane"] = lane
                normalized["recipient_id"] = recipient.recipient_id
                target_provenance.append(normalized)
            refusal_inputs = tuple(
                dict.fromkeys((*identities, *rendered.input_identities))
            )
            return {
                "candidates": (),
                "attempts": 1,
                "input_identities": refusal_inputs,
                "provenance": tuple((*provenance, *target_provenance)),
                "completion_reason": rendered.completion_reason,
                "refusal_code": rendered.refusal_code,
                "reason": rendered.reason,
            }
        candidates = _rendered_candidates(
            rendered,
            lane=lane,
            recipient=recipient,
        )
        if not candidates:
            return {
                "candidates": (),
                "attempts": 1,
                "input_identities": identities,
                "provenance": provenance,
                "completion_reason": "inapplicable",
                "refusal_code": "target_context_empty",
                "reason": "indexed donor query renderer returned no candidates",
            }
        return {
            "candidates": candidates,
            "attempts": 1,
            "input_identities": identities,
            "provenance": provenance,
            "completion_reason": "matched_pending_oracle",
            "reason": "indexed donor query rendered target context",
        }

    return callback


def _runtime_member(runtime: Any, *names: str) -> Any:
    if isinstance(runtime, Mapping):
        for name in names:
            if name in runtime:
                return runtime[name]
        return None
    for name in names:
        value = getattr(runtime, name, None)
        if value is not None:
            return value
    return None


def _typed_manifest(manifest: Any) -> RunManifest:
    if isinstance(manifest, RunManifest):
        return manifest
    if isinstance(manifest, Mapping):
        try:
            return RunManifest.from_dict(manifest)
        except (
            AttributeError,
            KeyError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise LaneError("production indexed adapters need a valid manifest") from exc
    raise LaneError("production indexed adapters need a typed RunManifest")


def _manifest_runtime_identity(manifest: RunManifest) -> str:
    """Return the one runtime identity explicitly bound by the manifest."""

    values: list[tuple[str, str]] = []
    for key in _RUNTIME_MANIFEST_KEYS:
        if key not in manifest.tool_identities:
            continue
        raw = manifest.tool_identities[key]
        try:
            value = validate_hash(raw, "manifest indexed runtime identity")
        except (TypeError, ValueError) as exc:
            raise LaneError("manifest indexed runtime identity is invalid") from exc
        values.append((key, value))
    if not values:
        raise LaneError("manifest has no explicit indexed runtime identity")
    identities = {value for _key, value in values}
    if len(identities) != 1:
        raise LaneError("manifest indexed runtime identities disagree")
    return values[0][1]


def _manifest_renderer_source_identity(manifest: RunManifest) -> str:
    """Return the target renderer byte identity bound by the factory manifest."""

    if _RENDERER_SOURCE_MANIFEST_KEY not in manifest.tool_identities:
        raise LaneError("manifest has no explicit target renderer source identity")
    raw = manifest.tool_identities[_RENDERER_SOURCE_MANIFEST_KEY]
    try:
        return validate_hash(raw, "manifest target renderer source identity")
    except (TypeError, ValueError) as exc:
        raise LaneError("manifest target renderer source identity is invalid") from exc


def _renderer_source_identity(repo_root: Path) -> str:
    """Hash the exact renderer source at the derived repository root.

    The runtime binding carries a source identity and the manifest carries the
    same identity, but neither value is an authority by itself.  At the
    production boundary the path is derived from the canonical run root, then
    the source bytes at that derived root are checked before a renderer can be
    reconstructed.  This keeps a caller-supplied renderer path or source
    object out of the identity decision.
    """

    try:
        root = Path(repo_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise LaneError("production renderer repository root cannot be resolved") from exc
    if not root.is_dir():
        raise LaneError("production renderer repository root is not a directory")
    candidate = root / "automation" / "search_target_renderer.py"
    current = root
    try:
        for component in ("automation", "search_target_renderer.py"):
            current = current / component
            if current.is_symlink():
                raise LaneError("production target renderer source cannot be a symlink")
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        if not resolved.is_file():
            raise LaneError("production target renderer source is not a file")
        data = resolved.read_bytes()
    except LaneError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise LaneError("production target renderer source cannot be read") from exc
    return hash_bytes(data)


def _reject_runtime_substitution(runtime: Any) -> None:
    """Refuse callback, live-path, or target-input injection on a runtime."""

    def check(value: Any, label: str) -> None:
        if isinstance(value, Mapping):
            names = set(value)
        else:
            try:
                names = set(vars(value))
            except TypeError:
                names = set()
        forbidden = sorted(names.intersection(_FORBIDDEN_RUNTIME_SUBSTITUTIONS))
        if forbidden:
            raise LaneError(
                "production indexed runtime cannot accept callback or live-path substitution in "
                + label
                + ": "
                + ", ".join(forbidden)
            )

    check(runtime, "runtime")
    binding = _runtime_member(runtime, "binding", "runtime_binding")
    if binding is not None:
        check(binding, "runtime binding")


def _validate_runtime_binding(
    runtime: Any,
    index: DonorIndexGeneration,
    *,
    manifest: RunManifest,
    renderer_source_identity: str | None = None,
) -> None:
    binding = _runtime_member(runtime, "binding", "runtime_binding")
    if binding is None:
        raise LaneError("production indexed runtime has no typed binding")
    derived_source_identity = renderer_source_identity
    runtime_id = _runtime_member(runtime, "runtime_id", "id")
    if not isinstance(runtime_id, str):
        raise LaneError("production indexed runtime has no runtime identity")
    try:
        validate_hash(runtime_id, "runtime_id")
    except (TypeError, ValueError) as exc:
        raise LaneError("production indexed runtime identity is invalid") from exc
    expected_runtime_id = _manifest_runtime_identity(manifest)
    if runtime_id != expected_runtime_id:
        raise LaneError("production indexed runtime differs from the manifest binding")
    generation_id = _runtime_member(
        binding,
        "donor_index_generation_id",
        "donor_index_id",
        "index_id",
    )
    artifact = _runtime_member(binding, "donor_index_artifact", "index_artifact")
    if generation_id is not None and generation_id != index.generation_id:
        raise LaneError("production runtime binding differs from its donor index")
    if generation_id is None:
        raise LaneError("production runtime binding has no donor index identity")
    if artifact is not None and artifact != index.artifact:
        if isinstance(artifact, Mapping):
            try:
                from .search_archive import ArtifactRef as _ArtifactRef
            except ImportError:  # direct invocation from the automation directory
                from search_archive import ArtifactRef as _ArtifactRef  # type: ignore
            try:
                artifact = _ArtifactRef.from_dict(artifact)
            except (
                AttributeError,
                KeyError,
                SearchValidationError,
                TypeError,
                ValueError,
            ) as exc:
                raise LaneError("production runtime donor artifact is invalid") from exc
        if artifact != index.artifact:
            raise LaneError("production runtime binding donor artifact differs")
    if artifact is None:
        raise LaneError("production runtime binding has no donor index artifact")
    compiler_identity = _runtime_member(binding, "compiler_identity")
    if compiler_identity is None:
        raise LaneError("production runtime binding has no compiler identity")
    if compiler_identity != manifest.compiler_identity:
        raise LaneError("production runtime binding compiler differs from the run manifest")
    config_identity = _runtime_member(binding, "config_identity")
    if config_identity is None:
        raise LaneError("production runtime binding has no configuration identity")
    if config_identity != manifest.config_identity:
        raise LaneError("production runtime binding configuration differs from the run manifest")
    renderer_identity = _runtime_member(binding, "renderer_identity")
    if renderer_identity is None:
        raise LaneError("production runtime binding has no target renderer identity")
    try:
        from .search_target_renderer import TARGET_RENDERER_IDENTITY
    except ImportError:  # direct invocation from the automation directory
        from search_target_renderer import TARGET_RENDERER_IDENTITY  # type: ignore
    try:
        renderer_identity = validate_hash(
            renderer_identity,
            "runtime renderer protocol identity",
        )
    except (TypeError, ValueError) as exc:
        raise LaneError("production runtime renderer protocol identity is invalid") from exc
    if renderer_identity != TARGET_RENDERER_IDENTITY:
        raise LaneError("production runtime renderer identity is unsupported")
    renderer_source_identity = _runtime_member(binding, "renderer_source_identity")
    if renderer_source_identity is None:
        raise LaneError("production runtime binding has no target renderer source identity")
    try:
        renderer_source_identity = validate_hash(
            renderer_source_identity,
            "runtime renderer source identity",
        )
    except (TypeError, ValueError) as exc:
        raise LaneError("production runtime renderer source identity is invalid") from exc
    expected_renderer_source_identity = _manifest_renderer_source_identity(manifest)
    if renderer_source_identity != expected_renderer_source_identity:
        raise LaneError(
            "production runtime renderer source identity differs from the run manifest"
        )
    if derived_source_identity is not None:
        try:
            derived_source_identity = validate_hash(
                derived_source_identity,
                "derived renderer source identity",
            )
        except (TypeError, ValueError) as exc:
            raise LaneError("derived renderer source identity is invalid") from exc
        if derived_source_identity != expected_renderer_source_identity:
            raise LaneError(
                "production runtime renderer source identity differs from derived source"
            )


def _runtime_archive_root(
    runtime: Any,
    run_archive: ContentAddressedArchive,
) -> Path:
    """Resolve the canonical runtime archive from the current run root.

    ``IndexedRuntimeGeneration`` intentionally remains a pure value and does
    not retain an open archive handle.  A factory run lives below
    ``<repo>/nonmatchings/<anchor>/search-runs/<run>``; deriving the sibling
    runtime path from that immutable layout avoids accepting caller-supplied
    arbitrary paths while still letting the adapter verify runtime artifacts.
    """

    if type(run_archive) is not ContentAddressedArchive:
        raise LaneError("production indexed runtime needs the canonical run archive")
    runtime_id = _runtime_member(runtime, "runtime_id", "id")
    if not isinstance(runtime_id, str):
        raise LaneError("production indexed runtime has no runtime identity")
    try:
        runtime_id = validate_hash(runtime_id, "runtime_id")
    except (TypeError, ValueError) as exc:
        raise LaneError("production indexed runtime identity is invalid") from exc
    raw_root = Path(run_archive.run_root)
    if raw_root.is_symlink():
        raise LaneError("run archive root is a symlink")
    try:
        current = raw_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LaneError("run archive root cannot be resolved") from exc
    if not current.is_dir():
        raise LaneError("run archive root is not a directory")
    nonmatchings = next(
        (ancestor for ancestor in (current, *current.parents) if ancestor.name == "nonmatchings"),
        None,
    )
    if nonmatchings is None:
        raise LaneError("run archive is outside the canonical nonmatchings root")
    try:
        relative = current.relative_to(nonmatchings)
    except ValueError as exc:
        raise LaneError("run archive is outside the canonical nonmatchings root") from exc
    if len(relative.parts) != 3 or relative.parts[1] != "search-runs":
        raise LaneError("run archive is not a canonical factory search run")
    anchor = relative.parts[0]
    if not anchor or anchor in {".", ".."}:
        raise LaneError("run archive anchor is invalid")
    try:
        validate_run_id(relative.parts[2], "run archive id")
    except (TypeError, ValueError) as exc:
        raise LaneError("run archive id is invalid") from exc
    if not nonmatchings.is_dir() or not current.is_dir():
        raise LaneError("canonical run archive root is missing")
    repo_root = nonmatchings.parent
    return repo_root / "nonmatchings" / "search-evidence" / "indexed-runtimes" / runtime_id.removeprefix("sha256:")


def _target_context_callbacks(
    manifest: RunManifest,
    target_index: Any,
    *,
    lane: str,
) -> tuple[
    Callable[[Recipient], DonorQuery],
    Callable[[Recipient, tuple[DonorSemanticClaim, ...]], Any],
]:
    """Build the typed target-query/render pair for one indexed lane.

    This is deliberately a small, archive-free composition boundary.  The
    public production constructor calls it only after verifying the runtime,
    donor archives, and target index.  Keeping the pair independently
    constructible lets the lower-level adapter test replay behavior without
    manufacturing a production runtime or passing live-path handles through
    the public constructor.
    """

    try:
        from .search_target_renderer import query_for_recipient
    except ImportError:  # direct invocation from the automation directory
        from search_target_renderer import query_for_recipient  # type: ignore

    def query_for(
        recipient: Recipient,
        *,
        target_index=target_index,
    ) -> DonorQuery:
        return query_for_recipient(
            manifest,
            target_index,
            recipient,
        )

    return query_for, _TargetContextRenderer(manifest, target_index, lane)


def production_indexed_adapters(
    manifest: RunManifest | Mapping[str, Any],
    runtime: Any,
    run_archive: ContentAddressedArchive,
) -> LaneAdapters:
    """Reconstruct both indexed callbacks from one verified runtime.

    The runtime owns the immutable donor generation and its integration-gate
    archive.  The current run archive owns target evidence, so target bytes
    are resolved once into a :class:`TargetIndex` before either lane callback
    is created.  Callbacks then read only those frozen values and never scan a
    repository or donor source tree.
    """

    typed_manifest = _typed_manifest(manifest)
    if type(run_archive) is not ContentAddressedArchive:
        raise LaneError("production indexed adapters need the run archive")
    if not any(lane in typed_manifest.selected_lanes for lane in INDEXED_LANES):
        raise LaneError("production indexed runtime is irrelevant to this manifest")

    # A published IndexedRuntimeGeneration is a pure typed value.  Its archive
    # handles are reconstructed only from the canonical runtime sibling of the
    # current run archive, and the generation is loaded and verified again so a
    # caller cannot relabel an arbitrary value as the manifest-bound runtime.
    try:
        from .search_indexed_runtime import (
            IndexedRuntimeBinding,
            IndexedRuntimeGeneration,
            IndexedRuntimeError,
            load_indexed_runtime,
        )
    except ImportError:  # direct invocation from the automation directory
        from search_indexed_runtime import (  # type: ignore
            IndexedRuntimeBinding,
            IndexedRuntimeGeneration,
            IndexedRuntimeError,
            load_indexed_runtime,
        )

    if type(runtime) is not IndexedRuntimeGeneration:
        raise LaneError(
            "production indexed adapters require a typed IndexedRuntimeGeneration"
        )
    _reject_runtime_substitution(runtime)
    runtime_fields = set(getattr(IndexedRuntimeGeneration, "__dataclass_fields__", {}))
    if set(vars(runtime)) != runtime_fields:
        raise LaneError("production indexed runtime carries noncanonical fields")
    if type(runtime.binding) is not IndexedRuntimeBinding:
        raise LaneError("production indexed runtime binding is not canonical")
    binding_fields = set(getattr(IndexedRuntimeBinding, "__dataclass_fields__", {}))
    if set(vars(runtime.binding)) != binding_fields:
        raise LaneError("production indexed runtime binding carries noncanonical fields")
    expected_runtime_id = _manifest_runtime_identity(typed_manifest)
    try:
        supplied_runtime_id = validate_hash(
            runtime.runtime_id,
            "production indexed runtime identity",
        )
    except (TypeError, ValueError) as exc:
        raise LaneError("production indexed runtime identity is invalid") from exc
    if supplied_runtime_id != expected_runtime_id:
        raise LaneError("production indexed runtime differs from the manifest binding")
    runtime_root = _runtime_archive_root(runtime, run_archive)
    repo_root = runtime_root.parents[3]
    renderer_source_identity = _renderer_source_identity(repo_root)
    if renderer_source_identity != _manifest_renderer_source_identity(typed_manifest):
        raise LaneError(
            "production target renderer source differs from the manifest binding"
        )
    try:
        loaded_runtime = load_indexed_runtime(runtime.runtime_id, repo=repo_root)
    except (IndexedRuntimeError, OSError, TypeError, ValueError) as exc:
        raise LaneError("manifest-bound indexed runtime cannot be loaded") from exc
    if loaded_runtime != runtime:
        raise LaneError("loaded indexed runtime differs from the supplied generation")
    runtime = loaded_runtime
    index = runtime.donor_index
    index_archive = ContentAddressedArchive(runtime_root)
    integration_archive = ContentAddressedArchive(runtime_root / "gate")
    _validate_runtime_binding(
        runtime,
        index,
        manifest=typed_manifest,
        renderer_source_identity=renderer_source_identity,
    )
    if type(index_archive) is not ContentAddressedArchive:
        raise LaneError("production indexed runtime donor archive is invalid")
    if type(integration_archive) is not ContentAddressedArchive:
        raise LaneError("production indexed runtime gate archive is invalid")
    if index.binding.compiler_identity != typed_manifest.compiler_identity:
        raise LaneError("production runtime compiler differs from the run manifest")
    if index.binding.config_identity != typed_manifest.config_identity:
        raise LaneError("production runtime configuration differs from the run manifest")
    try:
        from .search_target_renderer import load_target_index
    except ImportError:  # direct invocation from the automation directory
        from search_target_renderer import load_target_index  # type: ignore
    # The runtime is reusable donor evidence.  Target bytes belong to the
    # current manifest-bound run, so always resolve this index from that run's
    # archive rather than accepting a caller-supplied runtime target value.
    target_index = load_target_index(run_archive, typed_manifest)

    adapters: dict[str, Callable[[Recipient], Mapping[str, Any]]] = {}
    for lane in sorted(INDEXED_LANES):
        query_for, render_target_context = _target_context_callbacks(
            typed_manifest,
            target_index,
            lane=lane,
        )

        adapters[lane] = indexed_lane_adapter(
            index,
            lane=lane,
            expected_binding=index.binding,
            index_archive=index_archive,
            integration_archive=integration_archive,
            query_for=query_for,
            render_target_context=render_target_context,
        )
    return LaneAdapters.from_mapping(adapters)


__all__ = [
    "INDEXED_LANES",
    "indexed_lane_adapter",
    "production_indexed_adapters",
]
