"""Factory-bound full-build landing with durable source and queue recovery."""
from __future__ import annotations

from contextlib import nullcontext
import difflib
import json
from pathlib import Path
import re
import sys

from .search_archive import ContentAddressedArchive
from .search_types import ArtifactRef, canonical_bytes, hash_bytes, hash_canonical, validate_hash
from .search_supervisor import InstrumentedLandingOracle, DurableOracleError

TOOL_KEY = "full_oracle"
PROTOCOL = "sotn-automatic-landing-v1"
INTENTS = "landing-intents"
STOP_REASON = "oracle_candidate_found"
TOOL_FILES = (
    "automation/search_full_oracle.py", "automation/permuter_supervisor.py",
    "automation/win/worker_direct.py", "automation/scheduler.py",
    "automation/artifact_store.py", "automation/data_declarations.py",
    "automation/transplant.py", "Makefile",
)


def capture_binding(repo: Path) -> dict:
    from .search_run_factory import _safe_repo_file, _walk_regular_files
    files = [_safe_repo_file(repo, str(repo / name), "landing tool") for name in TOOL_FILES]
    for name in ("config", "tools/builds"):
        files.extend(path for path in _walk_regular_files(repo / name, repo, "landing inputs")
                     if "__pycache__" not in path.parts and path.suffix != ".pyc")
    return {
        "protocol": PROTOCOL,
        "policy": "stop_after_first_oracle_attempt",
        "files": [{"path": path.relative_to(repo).as_posix(),
                   "content_hash": hash_bytes(path.read_bytes()),
                   "byte_size": path.stat().st_size}
                  for path in sorted(set(files))],
    }


def validate_binding(binding: dict, identity: str) -> None:
    if (not isinstance(binding, dict) or set(binding) != {"protocol", "policy", "files"}
            or binding["protocol"] != PROTOCOL
            or binding["policy"] != "stop_after_first_oracle_attempt"
            or hash_canonical(binding) != identity):
        raise DurableOracleError("automatic landing binding differs")
    if not isinstance(binding["files"], list):
        raise DurableOracleError("automatic landing files must be a list")
    paths = []
    for item in binding["files"]:
        if (not isinstance(item, dict) or set(item) != {"path", "content_hash", "byte_size"}
                or not isinstance(item["path"], str) or not item["path"]
                or ":" in item["path"]
                or type(item["byte_size"]) is not int or item["byte_size"] < 0
                or Path(item["path"]).is_absolute()
                or ".." in Path(item["path"]).parts
                or "\\" in item["path"]):
            raise DurableOracleError("automatic landing tool path is invalid")
        validate_hash(item["content_hash"], "landing file hash")
        paths.append(item["path"])
    if len(paths) != len(set(paths)) or not set(TOOL_FILES).issubset(paths):
        raise DurableOracleError("automatic landing tool coverage differs")
    if "config/check.us.sha" not in paths:
        raise DurableOracleError("automatic landing has no complete checksum authority")


def _supervisor():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from . import permuter_supervisor
    return permuter_supervisor


def _worker(repo: Path):
    sys.path.insert(0, str(repo / "automation/win"))
    import worker_direct
    return worker_direct


def _without_comments(source: str) -> str:
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: "\n" * m[0].count("\n")
                  if m[0].startswith(("//", "/*")) else m[0], source)


def prepare_source(repo: Path, recipient: str, source: str):
    """Retain declared support while preserving every unrelated source span."""
    ps = _supervisor()
    from .search_lanes import _extract_function
    parts = recipient.split(":")
    if len(parts) != 3 or parts[0] != "us":
        raise DurableOracleError("automatic landing requires a US queue recipient")
    found = ps.find_stub(parts[2], parts[1])
    if found is None:
        raise DurableOracleError("automatic landing has no exact destination stub")
    path, asm_rel, _ = found
    relative = path.relative_to(repo).as_posix()
    ctx = {"src_rel": relative, "asm_rel": asm_rel}
    body = _extract_function(source, parts[2])
    if not body:
        raise DurableOracleError("automatic landing source has no complete target function")
    wd = _worker(repo)
    # These globally emitted parser declarations belong to isolated permutation.
    # The source writer independently derives declarations used by this body.
    source = re.sub(
        r"/\* Added by the permuter-seed writer\.[\s\S]*?"
        r"/\* End permuter-seed writer declarations\. \*/", "", source,
    )
    before = path.read_bytes()
    default = wd.virtual_apply(ctx, parts[2], body)
    lines = lambda text: [line.strip() for line in _without_comments(text).splitlines() if line.strip()]
    expected, supplied = lines(default), lines(source)
    support = []
    for tag, i, j, a, b in difflib.SequenceMatcher(None, expected, supplied, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag != "insert":
            raise DurableOracleError("candidate changes unrelated destination context")
        support.extend(wd._validated_support_declarations(supplied[a:b]))
    after = wd.virtual_apply(ctx, parts[2], body, support_declarations=support).encode("utf-8")
    return ctx, body, support, before, after


class FactoryLandingOracle(InstrumentedLandingOracle):
    """Reconstructable landing authority; queue completion follows durable proof."""

    def __init__(self, manifest, run_root: Path):
        self.manifest = manifest
        self.repo = Path(run_root).resolve().parents[3]
        super().__init__(run_root, manifest.tool_identities[TOOL_KEY], self._land)

    def intents(self):
        root = self.archive.artifacts_root / INTENTS
        if root.is_symlink():
            raise DurableOracleError("landing intent directory must not be a symlink")
        documents = []
        for path in sorted(root.glob("*.json")):
            raw = path.read_bytes()
            ref = ArtifactRef(hash_bytes(raw), path.relative_to(self.run_root).as_posix(), "application/json", len(raw))
            self.archive.verify(ref)
            doc = json.loads(raw)
            if (not isinstance(doc, dict) or set(doc) != {
                    "protocol", "manifest_identity", "oracle_identity", "recipient_id",
                    "candidate_id", "candidate", "source_path", "context", "support",
                    "body", "before", "after"}
                    or canonical_bytes(doc) != raw or doc.get("protocol") != PROTOCOL
                    or doc.get("manifest_identity") != hash_canonical(self.manifest.to_dict())
                    or doc.get("oracle_identity") != self.identity
                    or doc.get("recipient_id") not in self.manifest.queue_record_ids):
                raise DurableOracleError("landing intent is not bound to this run")
            relative = Path(doc["source_path"])
            if (relative.is_absolute() or ".." in relative.parts or not relative.parts
                    or relative.parts[0] != "src" or "\\" in doc["source_path"]
                    or ":" in doc["source_path"]
                    or set(doc["context"]) != {"src_rel", "asm_rel"}
                    or doc["context"]["src_rel"] != doc["source_path"]):
                raise DurableOracleError("landing intent source path escaped src")
            for name in ("candidate", "before", "after", "body"):
                reference = ArtifactRef.from_dict(doc[name])
                if reference.media_type != "text/x-c":
                    raise DurableOracleError("landing intent requires C source artifacts")
                self.archive.verify(reference)
            if doc["candidate_id"] != doc["candidate"]["content_hash"]:
                raise DurableOracleError("landing intent candidate identity differs")
            if not isinstance(doc["support"], list) or not all(isinstance(x, str) for x in doc["support"]):
                raise DurableOracleError("landing support declarations are invalid")
            documents.append((ref, doc))
        if len(documents) > 1:
            raise DurableOracleError("automatic run has more than one landing intent")
        return documents

    def _land(self, recipient, source, persist_terminal):
        ps = _supervisor()
        wd = _worker(self.repo)
        with ps._build_lock()():
            verify_landing_runtime(self.manifest, self.run_root)
            from . import scheduler
            scheduler._require_queue_owner("report")
            selected = [r for r in scheduler.Queue()._read() if r.get("id") == recipient]
            if len(selected) != 1 or not (selected[0].get("status") in {"todo", "near"}
                    or (selected[0].get("status") == "claimed" and selected[0].get("claimed_by") == self.owner)):
                raise DurableOracleError("landing recipient is no longer available")
            existing = self.intents()
            if existing:
                _, intent = existing[0]
                if (intent["recipient_id"] != recipient
                        or intent["candidate_id"] != hash_bytes(source.encode())):
                    raise DurableOracleError("a different candidate already owns this landing")
                path = self.repo / intent["source_path"]
                before = self.archive.verify(ArtifactRef.from_dict(intent["before"]))
                after = self.archive.verify(ArtifactRef.from_dict(intent["after"]))
                current = path.read_bytes()
                if current == after:
                    # No terminal receipt reached lookup. Recover only our exact
                    # proposed bytes, never an arbitrary operator or worker edit.
                    wd.restore(intent["context"], before.decode("utf-8"))
                elif current != before:
                    raise DurableOracleError("pending landing source has unrelated changes")
                ctx, body, support = intent["context"], self.archive.verify(
                    ArtifactRef.from_dict(intent["body"])).decode(), intent["support"]
            else:
                ctx, body, support, before, after = prepare_source(self.repo, recipient, source)
                intent = {
                    "protocol": PROTOCOL, "manifest_identity": hash_canonical(self.manifest.to_dict()),
                    "oracle_identity": self.identity, "recipient_id": recipient,
                    "candidate_id": hash_bytes(source.encode()), "candidate": self.archive.put_source(source).to_dict(),
                    "source_path": ctx["src_rel"], "context": ctx, "support": support,
                    "body": self.archive.put_source(body).to_dict(),
                    "before": self.archive.put_source(before.decode()).to_dict(),
                    "after": self.archive.put_source(after.decode()).to_dict(),
                }
                self.archive.put_json(intent, category=INTENTS)

            # Re-derive the exact proposal after a recovered source restore.
            actual_ctx, actual_body, actual_support, actual_before, actual_after = prepare_source(
                self.repo, recipient, source)
            if (actual_ctx != ctx or actual_body != body or actual_support != support
                    or actual_before != before or actual_after != after):
                raise DurableOracleError("reconstructed landing proposal differs from intent")

            def verified(detail):
                actual = (self.repo / ctx["src_rel"]).read_bytes()
                if actual != after:
                    raise DurableOracleError("applied source differs from the landing intent")
                persist_terminal("matched", detail)

            self._claim(recipient)
            result = ps.land_match(
                Path(), recipient.split(":")[2], body=body, rec_id=recipient,
                support_declarations=support, lock=lambda: nullcontext(),
                on_verified=verified,
                on_terminal=lambda matched, detail: persist_terminal("not_matched", detail),
            )
            return result

    def _persist(self, request, outcome, result):
        intents = self.intents()
        if not intents:
            raise DurableOracleError("automatic oracle has no durable source intent")
        ref, intent = intents[0]
        if (request.candidate_id != intent["candidate_id"]
                or request.recipient_id != intent["recipient_id"]):
            raise DurableOracleError("automatic oracle request differs from source intent")
        return super()._persist(request, outcome, {**result, "landing_intent": ref.to_dict()})

    def _load_document(self, path, request_id):
        if path.is_symlink():
            raise DurableOracleError("oracle receipt must not be a symlink")
        document = super()._load_document(path, request_id)
        intents = self.intents()
        result = document["result"]
        if (not intents or set(result) != {"candidate_id", "recipient_id", "detail", "landing_intent"}
                or result["landing_intent"] != intents[0][0].to_dict()
                or result["candidate_id"] != intents[0][1]["candidate_id"]
                or result["recipient_id"] != intents[0][1]["recipient_id"]
                or not isinstance(result["detail"], str)
                or document["outcome"] not in {"matched", "not_matched"}):
            raise DurableOracleError("automatic oracle terminal binding differs")
        return document

    def lookup(self, request_id):
        result = super().lookup(request_id)
        if result is None:
            return None
        intents = self.intents()
        if not intents or result["result"].get("landing_intent") != intents[0][0].to_dict():
            raise DurableOracleError("automatic oracle receipt lost its source intent")
        ps = _supervisor()
        with ps._build_lock()():
            self._report_queue(request_id, result["result"], result["outcome"])
        return result

    @property
    def owner(self):
        return "instrumented:" + self.manifest.run_id

    def _claim(self, recipient):
        from types import SimpleNamespace
        from . import scheduler
        def reserve(records):
            matches = [r for r in records if r.get("id") == recipient]
            if len(matches) != 1:
                raise DurableOracleError("landing queue recipient is missing or ambiguous")
            record = matches[0]
            if record.get("status") == "claimed" and record.get("claimed_by") == self.owner:
                return records, record
            if record.get("status") not in {"todo", "near"}:
                raise DurableOracleError("landing recipient was claimed or changed before apply")
            return scheduler._take(records, record, SimpleNamespace(worker=self.owner, worktree=False))
        scheduler._require_queue_owner("next")
        scheduler.Queue().transaction(reserve)

    def _report_queue(self, request_id, result, outcome):
        ps = _supervisor()
        from . import scheduler
        marker = "instrumented-oracle:" + request_id
        scheduler._require_queue_owner("report")
        records = scheduler.Queue()._read()
        selected = [record for record in records if record.get("id") == result["recipient_id"]]
        if len(selected) != 1:
            raise DurableOracleError("verified landing queue recipient is missing or ambiguous")
        record = selected[0]
        intent = self.intents()[0][1]
        expected = "after" if outcome == "matched" else "before"
        if (self.repo / intent["source_path"]).read_bytes() != self.archive.verify(ArtifactRef.from_dict(intent[expected])):
            raise DurableOracleError("terminal landing source differs from its oracle result")
        status = "matched" if outcome == "matched" else record.get("claimed_from", "todo")
        if record.get("status") == status and marker in (record.get("notes") or ""):
            return
        if record.get("status") != "claimed" or record.get("claimed_by") != self.owner:
            raise DurableOracleError("landing queue claim is no longer owned by this run")
        response = ps.report(result["recipient_id"], status,
                             f"{marker}; outcome={outcome}; candidate={result['candidate_id']}; "
                             f"run={self.manifest.run_id}; {result['detail']}",
                             proof=result["detail"] if outcome == "matched" else None, score=0)
        if response.startswith("QUEUE WRITE FAILED"):
            raise DurableOracleError(response)


def validate_landing_artifacts(manifest, archive, events=()):
    if TOOL_KEY not in manifest.tool_identities:
        return
    oracle = FactoryLandingOracle(manifest, archive.run_root)
    intents = oracle.intents()
    requests = {e.payload.request_id: e.payload for e in events if e.event_type == "oracle_requested"}
    if intents:
        intent = intents[0][1]
        matching = [r for r in requests.values() if r.candidate_id == intent["candidate_id"]
                    and r.recipient_id == intent["recipient_id"]
                    and r.candidate.source_artifact.to_dict() == intent["candidate"]]
        if len(matching) != 1:
            raise DurableOracleError("landing intent has no unique ledger request")
    # Validation is read-only. Queue reconciliation belongs to execution lookup.
    if oracle.store.is_symlink():
        raise DurableOracleError("automatic oracle service directory is a symlink")
    for path in oracle.store.glob("*.json"):
        request_id = "sha256:" + path.stem
        if request_id not in requests:
            raise DurableOracleError("oracle service receipt has no ledger request")
        document = oracle._load_document(path, request_id)
        if not intents or document["result"].get("landing_intent") != intents[0][0].to_dict():
            raise DurableOracleError("automatic oracle source receipt is corrupt")


def verify_landing_runtime(manifest, root):
    """Check landing inputs without re-discovering lanes changed by our build."""
    from . import search_run_factory as factory
    root = Path(root)
    repo = root.parents[3]
    factory.verify_factory_archive(root, manifest)
    archive = ContentAddressedArchive(root)
    index, _ = factory._load_index(root)
    tools = factory._archive_json(archive, index["tools"], "tools")
    binding = tools[TOOL_KEY]
    validate_binding(binding, manifest.tool_identities[TOOL_KEY])
    if capture_binding(repo) != binding:
        raise DurableOracleError("landing tools or checksum authority changed")
    modules = [*tools["core_modules"].values(), tools["factory"]["module"]]
    for entries in tools["lane_modules"].values():
        modules.extend(entries)
    for entry in modules:
        path = factory._safe_repo_file(repo, str(repo / entry["path"]), "landing module")
        if hash_bytes(path.read_bytes()) != entry["content_hash"]:
            raise DurableOracleError("landing execution module changed")
    config_id, config_path, _, _ = factory._config_identity(repo, tools["config"]["path"])
    schema_id, _, _, _ = factory._schema_identity(repo)
    compiler_id, _ = factory._compiler_identity(config_path, None)
    if (config_id != manifest.config_identity or schema_id != manifest.schema_identity
            or compiler_id != manifest.compiler_identity):
        raise DurableOracleError("landing compiler or configuration changed")
    frozen = factory._archive_json(archive, index["source"], "source")
    _, current = factory._source_identity(repo)
    old = {entry["path"]: entry for entry in frozen["files"]}
    new = {entry["path"]: entry for entry in current["files"]}
    intents = FactoryLandingOracle(manifest, root).intents()
    if intents:
        intent = intents[0][1]
        relative = intent["source_path"]
        before = intent["before"]
        after = intent["after"]
        if old.get(relative) != {"path": relative, "content_hash": before["content_hash"], "byte_size": before["byte_size"]}:
            raise DurableOracleError("landing original source differs from frozen repository")
        allowed = [{"path": relative, "content_hash": ref["content_hash"], "byte_size": ref["byte_size"]}
                   for ref in (before, after)]
        if new.get(relative) not in allowed:
            raise DurableOracleError("landing source has unrelated changes")
        new[relative] = old[relative]
    if new != old:
        raise DurableOracleError("repository source changed outside the landing intent")


class AutomaticLandingComplete(Exception):
    """Control boundary: a full build invalidates further frozen lane inputs."""


def terminal_result(coordinator):
    from .search_evaluator import search_funnel
    receipts = [e.payload for e in coordinator.events if e.event_type == "oracle_result_recorded"]
    if len(receipts) != 1 or receipts[0].outcome not in {"matched", "not_matched"}:
        raise DurableOracleError("automatic landing requires one terminal oracle result")
    reason = "oracle_" + receipts[0].outcome
    stops = [e.payload for e in coordinator.events if e.event_type == "run_stopped"]
    if not stops or stops[-1].reason != STOP_REASON:
        coordinator.stop(reason=STOP_REASON, resumable=False)
    return {"command": "instrumented-run", "ok": True,
            "run_id": coordinator.manifest.run_id, "run_root": str(coordinator.archive.run_root),
            "reason": reason, "state": coordinator.state_dict(),
            "funnel": search_funnel(coordinator.manifest, coordinator.events, coordinator.archive)}


def recover_landing(coordinator):
    """Finish only the durable oracle task; never redispatch discovery after apply."""
    from .search_coordinator import TaskResult
    from .search_evaluator import evaluation_receipts
    requests = [e.payload for e in coordinator.events if e.event_type == "oracle_requested"]
    if not requests:
        raise DurableOracleError("landing intent has no ledger request")
    if len(requests) != 1:
        raise DurableOracleError("automatic landing has multiple oracle requests")
    request = requests[0]
    # Lookup completes a previously verified queue transition without rebuilding.
    coordinator.oracle.lookup(request.request_id)
    terminal = [e.payload for e in coordinator.events if e.event_type == "task_completed"
                and e.payload.task_id == request.task_id]
    if not terminal:
        evaluations = [e.payload for e in coordinator.events if e.event_type == "evaluation_completed"
                       and e.payload.task_id == request.task_id]
        refs = [ref for ref, doc in evaluation_receipts(coordinator.archive)
                if doc["binding"]["task_id"] == request.task_id]
        if len(evaluations) != 1 or len(refs) != 1:
            raise DurableOracleError("pending oracle lost its actual evaluation")
        mutation = next((e.payload for e in coordinator.events
                         if e.event_type == "mutation_materialized"
                         and getattr(e.payload, "mutation_id", None) == request.candidate.mutation_id), None)
        coordinator.commit_epoch((TaskResult(
            task_id=request.task_id, candidate=request.candidate, mutation=mutation,
            evaluation=evaluations[0], result_artifacts=tuple(refs),
            reason="candidate evaluated against archived target",
        ),))
    return terminal_result(coordinator)


def finalize_recorded_landing(coordinator):
    """Close a fully reported historical attempt without executing bound tools.

    Harness updates must not force an already verified, reported landing back
    through source application. Archive and ledger validation remain mandatory;
    only this terminal bookkeeping can proceed without current tool equality.
    """
    from . import scheduler
    receipts = [e.payload for e in coordinator.events if e.event_type == "oracle_result_recorded"]
    requests = {e.payload.request_id: e.payload for e in coordinator.events if e.event_type == "oracle_requested"}
    completed = {e.payload.task_id for e in coordinator.events if e.event_type == "task_completed"}
    if len(receipts) != 1 or receipts[0].request_id not in requests:
        return None
    receipt = receipts[0]
    request = requests[receipt.request_id]
    if request.task_id not in completed:
        return None
    oracle = coordinator.oracle
    document = oracle._load_document(oracle._path(request.request_id), request.request_id)
    if document["result"] != dict(receipt.result) or document["outcome"] != receipt.outcome:
        raise DurableOracleError("recorded landing differs from its terminal service receipt")
    # A completed stop is already historical proof and has no remaining writes.
    if any(e.event_type == "run_stopped" and e.payload.reason == STOP_REASON
           and not e.payload.resumable for e in coordinator.events):
        return terminal_result(coordinator)
    records = [json.loads(line) for line in scheduler.QUEUE.read_text().splitlines() if line.strip()]
    selected = [r for r in records if r.get("id") == request.recipient_id]
    marker = "instrumented-oracle:" + request.request_id
    if len(selected) != 1 or marker not in (selected[0].get("notes") or ""):
        return None
    record = selected[0]
    expected_status = "matched" if receipt.outcome == "matched" else record.get("claimed_from", "todo")
    if record.get("status") != expected_status:
        return None
    intent = oracle.intents()[0][1]
    expected = "after" if receipt.outcome == "matched" else "before"
    if (oracle.repo / intent["source_path"]).read_bytes() != oracle.archive.verify(ArtifactRef.from_dict(intent[expected])):
        raise DurableOracleError("reported landing source differs before terminal closure")
    return terminal_result(coordinator)
