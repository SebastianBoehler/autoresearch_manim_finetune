from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from mac_pipeline.grouped_split import assign_split_groups
from mac_pipeline.versioned_api import enrich_case_with_api_context


ALLOWED_DECISIONS = {"accept", "quarantine", "rewrite"}


@dataclass(frozen=True)
class CurationResult:
    accepted: list[dict[str, Any]]
    quarantine: list[dict[str, Any]]
    rewrite: list[dict[str, Any]]

    @property
    def summary(self) -> dict[str, int]:
        return {
            "accepted": len(self.accepted),
            "quarantine": len(self.quarantine),
            "rewrite": len(self.rewrite),
            "source": len(self.accepted) + len(self.quarantine) + len(self.rewrite),
        }


def records_digest(records: list[dict[str, Any]]) -> str:
    canonical = "\n".join(
        json.dumps(record, sort_keys=True, separators=(",", ":"))
        for record in records
    )
    return hashlib.sha256((canonical + "\n").encode()).hexdigest()


def apply_curation(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    public_symbols: set[str],
) -> CurationResult:
    _validate_manifest(records, manifest)
    decisions = {entry["case_id"]: entry for entry in manifest["decisions"]}
    runtime = manifest["target_runtime"]
    verification = manifest["render_verification"]
    accepted: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    rewrite: list[dict[str, Any]] = []

    for record in records:
        decision = decisions[record["case_id"]]
        disposition = decision["decision"]
        if disposition == "accept":
            enriched = enrich_case_with_api_context(
                record,
                manim_version=runtime["manim_version"],
                python_version=runtime["python_version"],
                renderer=runtime["renderer"],
                public_symbols=public_symbols,
            )
            enriched["dataset_version"] = manifest["dataset_version"]
            enriched["curation_decision"] = "accept"
            enriched["curation_reason"] = decision["reason"]
            enriched["render_verified"] = True
            enriched["render_verified_version"] = verification["manim_version"]
            enriched["render_quality"] = verification["quality"]
            accepted.append(enriched)
            continue
        excluded = dict(record)
        excluded["curation_decision"] = disposition
        excluded["curation_reason"] = decision["reason"]
        (quarantine if disposition == "quarantine" else rewrite).append(excluded)

    return CurationResult(
        accepted=assign_split_groups(accepted),
        quarantine=quarantine,
        rewrite=rewrite,
    )


def _validate_manifest(records: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported curation manifest schema_version.")
    if manifest.get("expected_case_count") != len(records):
        raise ValueError("Curation manifest expected_case_count does not match source records.")
    if manifest.get("source_sha256") != records_digest(records):
        raise ValueError("Curation manifest source_sha256 does not match source records.")

    source_ids = {str(record["case_id"]) for record in records}
    entries = manifest.get("decisions", [])
    decision_ids = [str(entry.get("case_id")) for entry in entries]
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("Curation manifest contains duplicate case decisions.")
    missing = sorted(source_ids - set(decision_ids))
    unknown = sorted(set(decision_ids) - source_ids)
    if missing:
        raise ValueError(f"Curation manifest is missing decisions for: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"Curation manifest references unknown cases: {', '.join(unknown)}")
    for entry in entries:
        if entry.get("decision") not in ALLOWED_DECISIONS:
            raise ValueError(f"Unsupported curation decision for {entry.get('case_id')}.")
        if not str(entry.get("reason") or "").strip():
            raise ValueError(f"Curation decision for {entry.get('case_id')} needs a reason.")

    runtime = manifest.get("target_runtime", {})
    verification = manifest.get("render_verification", {})
    if (
        verification.get("manim_version") != runtime.get("manim_version")
        or verification.get("renderer") != runtime.get("renderer")
    ):
        raise ValueError("Curation manifest render verification runtime does not match target_runtime.")
    verified_ids = {str(case_id) for case_id in verification.get("successful_case_ids", [])}
    accepted_ids = {
        str(entry["case_id"])
        for entry in entries
        if entry.get("decision") == "accept"
    }
    unverified = sorted(accepted_ids - verified_ids)
    if unverified:
        raise ValueError(
            "Curation manifest accepted cases lack render evidence: "
            + ", ".join(unverified)
        )
