"""Conservative, non-model source-completeness checks for a CR item."""
import re


def source_input_issues(question):
    q=question if isinstance(question,dict) else question.model_dump()
    passage=(q.get('passage') or '').strip();stem=(q.get('stem') or '').strip()
    issues=[]
    if not passage and not stem:issues.append('missing_question_text')
    # An older importer put a lone question prompt in passage, with no stem.
    query_only=not passage or (not stem and re.match(r'^(?:Which|What|The (?:argument|passage|conclusion)|\w+[’\']s argument)\b',passage,re.I))
    query=stem if not passage else passage
    needs_context=re.search(r'\babove\b|\b(?:the|this|that) (?:passage|argument|conclusion|evidence|reasoning)\b|\w+[’\']s argument',query,re.I)
    if query_only and needs_context and not re.search(r'_{2,}',passage):issues.append('missing_referenced_stimulus')
    return issues
