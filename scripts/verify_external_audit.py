"""Check documentary-audit records/hashes; never fetch or infer survey data."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    metadata = Path("research/reading_notes/external_source_access.json")
    card = Path("research/external_data_card.md")
    feasibility = Path("reports/external_pilot_feasibility.md")
    data = json.loads(metadata.read_text())
    require(data["task_id"] == "W1-REAL-AUDIT", "wrong task")
    require(len(set(data["dataset_ids"])) == 2, "dataset scope exceeded")
    require(data["raw_lightcurves_downloaded"] == 0, "unexpected raw downloads")
    require(data["scientific_inference_runs"] == 0, "unexpected external experiment")
    require(data["scientific_fitting_wall_seconds"] == 0, "unexpected fitting cost")
    require(data["third_party_messages_sent"] == data["mass_downloads"] == 0, "scope breach")
    require(data["external_classification_outcome"] == "NOT_RUN", "outcome mismatch")
    require("NOT_RUN" in card.read_text() and "NOT_RUN" in feasibility.read_text(), "false claim")
    sources = data["sources"]
    require(len({s["source_id"] for s in sources}) == len(sources) == 4, "source mismatch")
    checked, absent = [], []
    cache = Path("artifacts/external_audit_docs")
    for source in sources:
        require(source["dataset_id"] in data["dataset_ids"], "third dataset")
        require(source["read_scope"] and source["not_read"], "missing reading scope")
        require(not source["redistributed_full_text"], "unlicensed source mirror")
        if source["sha256"] is not None:
            require(source["status"] == 200, "hash assigned to failed request")
            local = cache / (source["source_id"] + ".html")
            if local.exists():
                require(digest(local) == source["sha256"], "local document hash changed")
                checked.append(source["source_id"])
            else:
                absent.append(source["source_id"])
    api = next(s for s in sources if s["source_id"] == "ztf_lightcurve_api")
    pdf = next(s for s in sources if s["source_id"] == "ztf_dr24_notes")
    require(not api["full_text_read"] and api["version_read"] is None, "unread API claimed read")
    require(pdf["sha256_pdf_bytes"] is None, "unavailable PDF hash invented")
    rendered = cache / "web_selected_rendering.json"
    if rendered.exists():
        require(
            digest(rendered) == data["reviewed_web_rendering"]["sha256"],
            "reviewed rendering changed",
        )
        checked.append("selected_web_rendering_not_pdf_bytes")
    else:
        absent.append("selected_web_rendering_not_pdf_bytes")
    result = {
        "status": "PASS_DOCUMENTARY_RECORDS_ONLY",
        "checked_utc": datetime.now(UTC).isoformat(),
        "verified_scope": "Record consistency and locally available document hashes only",
        "scientific_or_legal_validation": False,
        "raw_or_labels_or_crossmatch_verified": False,
        "files": {str(p): digest(p) for p in [metadata, card, feasibility]},
        "local_cache_hashes_checked": checked,
        "local_cache_unavailable": absent,
        "external_classification_outcome": data["external_classification_outcome"],
        "dataset_count": len(data["dataset_ids"]),
        "raw_lightcurves_downloaded": 0,
        "scientific_inference_runs": 0,
        "limitations": data["limitations"],
    }
    output = Path("reports/checks/external_audit_verifier.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
