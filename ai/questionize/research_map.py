"""Public literature-to-code-to-run projection. Never reads private artifacts."""
from pathlib import PurePosixPath
from urllib.parse import urlsplit


def public_path(value):
    return isinstance(value, str) and not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts and value.startswith(("ai/", "api/", "research/", "docs/"))


def public_url(value):
    if not isinstance(value, str):
        return False
    u = urlsplit(value)
    return u.scheme == "https" and u.hostname in ("arxiv.org", "aclanthology.org", "github.com", "doi.org", "openreview.net", "wisconsin.pressbooks.pub", "forallx.openlogicproject.org") and not u.username and not u.password


def project_registry(registry, rows):
    from .scoreboard import scope_of
    if registry.get("schema_version") != 1:
        raise ValueError("Unsupported evidence registry")
    papers = []
    for paper in registry.get("papers", []):
        if not public_url(paper.get("url")):
            raise ValueError("Invalid primary-source URL")
        entry = {k: paper[k] for k in ("id", "title", "url", "capabilities", "claim", "limitations", "implementation_status", "review_status", "protocols")}
        entry["implementation_paths"] = [p for p in paper.get("implementation_paths", []) if public_path(p)]
        conditions = paper.get("result_conditions")
        entry["runs"] = [{"run_id": r["run_id"], "protocol": r["protocol"], "scope": scope_of(r),
            "report_path": f"research/results/{r['protocol']}.md"} for r in rows if r.get("protocol") in entry["protocols"]
            and (conditions is None or any(c in r.get("summary", {}) for c in conditions))]
        papers.append(entry)
    capture_fields = ("id", "protocol", "capabilities", "total", "eligible", "held_flagged", "repaired_items", "restored_emphasis_items",
        "restored_identifiers", "visual_review_scope", "independent_human_review", "dataset_hash", "manifest_hash", "parent_hash", "pdf_hash",
        "remaining_mechanical_issues", "membership", "report_path", "stimulus_omissions_repaired", "reference_explanation_repairs",
        "ocr_pages", "printed_keys_crosschecked", "ocr_engines", "stimulus_regions_aligned", "unmatched_regions_for_review")
    # Metric summaries are prepared explicitly by the research operator. Do not merge run outputs.
    metric_keys = {"expected", "completed", "errors", "calls", "parents", "correct", "n", "accuracy", "ci95", "coverage", "corrected", "corrupted",
        "unrated_explanations", "explanation_errors", "solver", "legacy", "guarded", "judge", "by_type", "valid_control", "wrong_key",
        "duplicate_correct_option", "contradictory_explanation", "missing_emphasis", "legacy_accepted", "guarded_accepted", "deterministically_blocked",
        "rejected", "false_accepts", "completion_first", "completion_repeat", "previous_test", "repeat_disagreements",
        "format_contract", "normal_accepted", "normal_n", "missing_blank_blocked", "defect_n", "baseline", "candidate",
        "first_draft_pass_rate", "first_draft_pass_rate_n", "first_draft_pass_rate_ci95", "passed", "gained", "lost", "adopt",
        "evidence_contract_passed", "source_text_roles_equal", "statuses", "ai_estimated", "unconfirmed", "disputed", "supplied_reference",
        "detailed_available", "analysis_completed", "explanation_withheld"}
    def metrics(value):
        if isinstance(value, dict):
            return {k: metrics(v) for k, v in value.items() if k in metric_keys}
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        if isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
            return value
        return None
    evaluations = []
    for e in registry.get("evaluations", []):
        entry = {k: e[k] for k in ("run_id", "protocol", "scope", "limitations", "decision", "report_path") if k in e}
        entry["summary"] = metrics(e.get("summary", {}))
        evaluations.append(entry)
    asset_fields = ("id", "namespace", "derivation", "evidence_status", "rights_scope", "count", "unit", "artifact_hash", "limitation")
    return {"reviewed_at": registry.get("reviewed_at"), "review_scope": registry.get("review_scope"), "papers": papers,
        "knowledge_assets": [{k: e[k] for k in asset_fields if k in e} for e in registry.get("knowledge_assets", [])],
        "capture_audits": [{k: e[k] for k in capture_fields if k in e} for e in registry.get("capture_audits", [])],
        "evaluations": evaluations, "knowledge_policy": {k: registry.get("knowledge_policy", {}).get(k, "")
            for k in ("expert_reference", "user_experience", "promotion", "rights")}}
