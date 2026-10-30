"""Deterministic defects; these checks do not establish semantic correctness."""
import re
import unicodedata

INTEGRITY_VERSION = "integrity-0.2"


def is_completion(stem: str) -> bool:
    return bool(re.search(r"\b(?:completes?|completing)\s+(?:the\s+)?(?:passage|argument|statement|sentence)\b", stem, re.I))


def integrity_issues(question) -> list[str]:
    normalized = [" ".join(unicodedata.normalize("NFKC", c.text).casefold().split()) for c in question.choices]
    found = []
    if len(set(normalized)) != len(normalized):
        found.append("duplicate_choice_text")
    if any(not s for s in normalized):
        found.append("empty_choice_text")
    # A dangling connective can be intentional in this format, but the printed blank is
    # essential source structure. Do not infer a blank or silently repair a live upload.
    if is_completion(question.stem) and not re.search(r"_{2,}|[—–]{2,}|\[BLANK\]", question.passage):
        found.append("missing_completion_blank")
    if re.search(r"bold\s*face", question.stem, re.I):
        spans = re.findall(r"\[BOLD_(\d+)\].+?\[/BOLD_\1\]|\*\*([^*]+)\*\*", question.passage, re.S)
        required = 2 if re.search(r"\btwo\b", question.stem, re.I) else 1
        if len(spans) < required:
            found.append("missing_required_emphasis")
    return found
