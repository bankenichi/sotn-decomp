"""Read-only lane adapters backed by the immutable donor query index.

The indexed lane is the boundary between the archive-verified donor query and
the ordinary lane discovery normalizer.  A query is bound once when the
adapter is created.  Per-recipient callbacks then create one typed query,
render only semantic claims, and return ordinary discovery values carrying
the complete immutable query provenance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
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
        LaneError,
        Recipient,
        SubsetViolation,
    )
    from .search_types import hash_bytes, hash_canonical, validate_hash
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
        LaneError,
        Recipient,
        SubsetViolation,
    )
    from search_types import hash_bytes, hash_canonical, validate_hash  # type: ignore


INDEXED_LANES = frozenset({"multi_donor", "cfg_dataflow"})
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

    claims: dict[str, DonorSemanticClaim] = {}
    for hit in result.hits:
        claim = DonorSemanticClaim.from_evidence(hit.entry.evidence)
        claims.setdefault(claim.claim_identity, claim)
    return tuple(claims[identity] for identity in sorted(claims))


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
        LaneCandidate | Sequence[LaneCandidate],
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
        rendered = render_target_context(recipient, claims)
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


__all__ = ["INDEXED_LANES", "indexed_lane_adapter"]
