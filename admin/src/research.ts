export interface Capability { id: string; name: string; bar: string; metric: string; unit: string; direction: string }
export interface Qualification { id: string; summary: string; report_url?: string }
export interface Run {
  run_id: string; protocol: string; protocol_version: number; started_at: string; subject: string;
  scope: "full" | "trial" | "regression"; n_items: number; dataset_id: string; dataset_hash: string;
  split: string; prompts_hash: string; git_sha: string; models: Record<string, string>;
  judge: Record<string, unknown>; memory: { hash: string; lessons: number } | null;
  baseline_run: string | null; note: string; capabilities: string[]; measured_capabilities: string[];
  qualifications?: Qualification[];
}
export interface Comparison { b?: number; c?: number; p?: number; n?: number; baseline_accuracy?: number; diff_ci95?: [number, number] }
export interface Measurement {
  run_id: string; capability: string; subject: string; condition: string; scope: "full" | "trial" | "regression";
  metric: string; value: number; n: number | null; ci95: [number, number] | null;
  expected_n: number | null; complete: boolean | null; calls?: number; ece?: number;
  vs_B0?: Comparison; vs_baseline?: Comparison;
}
export interface ResearchData {
  schema_version: number; updated_at: string | null; capabilities: Capability[];
  subjects: string[]; runs: Run[]; records: Measurement[];
  evidence?: EvidenceRegistry;
  budget_studies?: BudgetStudy[];
  mastery_studies?: MasteryStudy[];
}

export interface MasteryMetric {
  n: number; expected_n: number; correct: number; accuracy: number | null; ci95?: [number,number]; errors: number; repair_errors: number;
  calls: number; normalised_usd: number; estimated_billed_usd: number; input_tokens: number; output_tokens: number;
  reasoning_tokens: number; cached_tokens: number; mean_seconds: number; tool_witnesses: number; repair_rescues: number; repair_harms: number;
  hard_trials: number; hard_correct: number; hard_unique: number; hard_closed: number; usage_complete: boolean;
  model?: string; effort?: string; method?: string; baseline?: string; envelope?: number;
  comparison?: {b?:number;c?:number;p?:number;difference?:number;n?:number;diff_ci95?:[number,number]};
}
export interface MasteryPhase {
  registered:number; evaluated:number; unique_questions:number; budget_limited:boolean; completed:boolean;
  conditions:Record<string,MasteryMetric>; roles:Record<string,Record<string,MasteryMetric>>;
}
export interface MasteryStudy {
  schema_version:number; run_id:string; started_at:string; candidate:string; baseline:string; interpretation:string;
  decision:string; candidate_deployed:boolean; official_closed:boolean; cost_accounting_complete:boolean;
  confirmation_cost_accounting_complete?:boolean; blinding_passed?:boolean; audited_requests?:number;matched_requests?:number;protocol_version?:number;
  preparation?:{restored_questions?:number;invalid_evaluated_questions?:number;invalid_phase_generation_calls?:number;invalid_phase_normalised_usd?:number;invalid_phase_estimated_billed_usd?:number;aborted_reservation_upperbound_usd?:number;keys_changed?:number;choices_changed?:number;source_test_roles_preserved?:boolean};
  unique_evaluated:number; condition_responses:number; budget_limit_usd:number; charged_usd:number; unknown_usage:number;
  normalised_usd:number; estimated_billed_usd:number; manifest_hash:string; policy_hash:string; source_hash:string;
  report_path:string; protocol_path:string; clarification_path:string;
  split:{counts:Record<string,number>;groups:Record<string,number>;hashes:Record<string,string>;confirmation_overlap:number;total_gmat_records:number};
  phases:Record<string,MasteryPhase>;
}

export interface BudgetCondition {
  n: number; correct: number; accuracy: number; ci95?: [number, number]; errors: number; calls: number;
  normalised_usd: number; estimated_billed_usd: number; input_tokens: number; output_tokens: number;
  reasoning_tokens: number; cached_tokens: number; mean_seconds: number; usage_complete: boolean; budget_violations: number;
  vs_baseline?: { b?: number; c?: number; p?: number; difference?: number; diff_ci95?: [number, number] };
}
export interface BudgetStudy {
  run_id: string; started_at: string; model: string; reasoning_effort: string; envelope_usd: number;
  decision: "held" | "confirmation_required"; candidate_deployed: boolean; cost_comparison_valid: boolean;
  split: { counts: Record<string, number>; groups: Record<string, number>; membership_hashes: Record<string, string>; cross_partition_group_overlap: number };
  conditions: Record<string, BudgetCondition>; diagnostics: Record<string, number>; slices: Record<string, Record<string, number>>;
  training_normalised_usd: number; training_estimated_billed_usd: number; training_calls: number; training_failures: number; procedure_count: number;
  development_normalised_usd?: number; development_estimated_billed_usd?: number; development_calls?: number;
  memory_retrieval_covered?: number;
  memory_hash: string; manifest_hash: string; runner_hash: string; client_hash: string; report_path: string; protocol_path: string;
  rates: Record<string, number>; price_url: string; price_reviewed: string;
  operational_errors?: Record<string, Record<string, number>>;
  blinding_audit?: { passed: boolean; training_requests_checked?: number; training_requests_matched?: number; evaluation_requests_checked?: number; evaluation_requests_matched?: number; reference_pattern_hits?: number };
}

export interface PaperEvidence {
  id: string; title: string; url: string; capabilities: string[]; claim: string; limitations: string;
  implementation_status: string; review_status: string; implementation_paths: string[]; protocols: string[];
  runs: { run_id: string; protocol: string; scope: string; report_path: string }[];
}
export interface EvidenceRegistry {
  reviewed_at: string; review_scope: string; papers: PaperEvidence[];
  capture_audits: { id: string; total: number; eligible: number; held_flagged: number; repaired_items: number;
    restored_emphasis_items: number; restored_identifiers: number; dataset_hash: string; visual_review_scope: string;
    independent_human_review: boolean; membership: string; report_path: string; stimulus_omissions_repaired?: number;
    printed_keys_crosschecked?: number; ocr_pages?: number; ocr_engines?: string; unmatched_regions_for_review?: number }[];
  evaluations: { run_id: string; protocol: string; scope: string; decision: string; limitations: string; report_path: string;
    summary: Record<string, any> }[];
  knowledge_policy: Record<string, string>;
  knowledge_assets?: { id: string; namespace: string; derivation: string; evidence_status: string; rights_scope: string;
    count: number; unit: string; artifact_hash: string; limitation: string }[];
}

export const GROUPS = [
  { id: "C1", name: "Capture", detail: "Read and reconstruct" },
  { id: "C2", name: "Understand", detail: "Skills, objectives, traps" },
  { id: "C3", name: "Solve & explain", detail: "Answers and reasoning" },
  { id: "C4", name: "Diagnose", detail: "Learner misconceptions" },
  { id: "C5", name: "Write practice", detail: "Original, verified items" },
  { id: "C6", name: "Choose practice", detail: "Recommendations and gains" },
];
export const subjectName = (subject: string) => ({ CR: "Critical Reasoning", RC: "Reading Comprehension" }[subject] ?? subject);
export const percentage = (value: number | null | undefined) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;
export const baseCondition = (condition: string) => condition.replace(/\+M$/, "");
export const shortId = (id: string) => id.split("-").at(-1) ?? id;
export const timestamp = (date: string | null | undefined) => date
  ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC" }).format(new Date(date)) + " UTC" : "No runs yet";

export function measurements(data: ResearchData, subject: string, capability: string, scope: string, condition = "all") {
  return data.records.filter((record) => record.subject === subject && record.capability === capability
    && (scope === "all" || record.scope === scope) && (condition === "all" || record.condition === condition));
}

export function comparisonView(before: Run | undefined, after: Run | undefined, left: Measurement | undefined, right: Measurement | undefined) {
  const positiveCount = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value > 0;
  const sameMeasure = !!left && !!right && left.capability === right.capability && left.metric === right.metric && left.subject === right.subject;
  // Legacy E1 comparisons contain solving accuracy, not a baseline value for any other metric.
  const paired = before?.run_id === after?.baseline_run && sameMeasure && right?.metric === "accuracy" && right.capability === "C3.1"
    && baseCondition(left!.condition) === baseCondition(right.condition) ? right.vs_baseline : undefined;
  const baselineAccuracy = paired?.baseline_accuracy;
  const pairedSampleKnown = positiveCount(left?.n) && positiveCount(right?.n) && right.n <= left.n
    && left.run_id === before?.run_id && right.run_id === after?.run_id && left.expected_n === left.n && before.n_items === left.n
    && left.complete === true && before?.scope === "full" && !!before.dataset_hash && before.dataset_hash === after?.dataset_hash
    && !!before.split && before.split === after?.split && (paired?.n == null || paired.n === right.n);
  const usePairedBaseline = pairedSampleKnown && typeof baselineAccuracy === "number" && Number.isFinite(baselineAccuracy)
    && baselineAccuracy >= 0 && baselineAccuracy <= 1;
  const leftValue = usePairedBaseline ? baselineAccuracy : left?.value ?? null;
  const leftN = usePairedBaseline ? right!.n : left?.n ?? null;
  const rightValue = right?.value ?? null;
  const rightN = right?.n ?? null;
  const difference = sameMeasure && positiveCount(leftN) && leftN === rightN && leftValue != null && rightValue != null
    ? (rightValue - leftValue) * 100 : null;
  return {
    leftValue, leftN, rightValue, rightN, difference, paired,
    matchedSubset: usePairedBaseline && right!.n! < left!.n!, baselineTotal: left?.n ?? null,
  };
}

export function comparisonIssues(before: Run, after: Run, left?: Measurement, right?: Measurement): string[] {
  const issues: string[] = [];
  if (before.qualifications?.length || after.qualifications?.length) issues.push("These runs have unresolved data or method qualifications; review the evaluation notes.");
  const positiveCount = (value: unknown) => typeof value === "number" && Number.isInteger(value) && value > 0;
  for (const [key, label] of [["protocol", "Protocol"], ["subject", "Subject"], ["dataset_id", "Dataset ID"], ["dataset_hash", "Dataset"], ["split", "Split"], ["prompts_hash", "Prompt/code hash"]] as const) {
    if (!before[key] || !after[key]) issues.push(`${label} was not recorded for both runs.`);
    else if (before[key] !== after[key]) issues.push(`${label} differs between runs.`);
  }
  if (!positiveCount(before.protocol_version) || !positiveCount(after.protocol_version)) issues.push("Protocol versions were not recorded for both runs.");
  else if (before.protocol_version !== after.protocol_version) issues.push("Protocol versions differ between runs.");
  const sorted = (value: Record<string, unknown>) => JSON.stringify(Object.entries(value ?? {}).sort(([a], [b]) => a.localeCompare(b)));
  const recorded = (value: Record<string, unknown> | undefined) => value && Object.keys(value).length > 0;
  if (!recorded(before.models) || !recorded(after.models)) issues.push("Models were not recorded for both runs.");
  else if (sorted(before.models) !== sorted(after.models)) issues.push("Models differ between runs.");
  if (!recorded(before.judge) || !recorded(after.judge)) issues.push("Judge settings were not recorded for both runs.");
  else if (sorted(before.judge) !== sorted(after.judge)) issues.push("Judge settings differ between runs.");
  if (before.scope === "regression" || after.scope === "regression") issues.push("Recorded policy regression results are not fresh model-quality evaluations.");
  else if (!["full", "trial"].includes(before.scope) || !["full", "trial"].includes(after.scope)) issues.push("Evaluation scope was not recorded for both runs.");
  else if (before.scope !== "full" || after.scope !== "full") issues.push("This comparison includes a trial run.");
  if (!positiveCount(before.n_items) || !positiveCount(after.n_items)) issues.push("Expected run sample sizes were not recorded for both runs.");
  else if (before.n_items !== after.n_items) issues.push("The expected run sample sizes differ.");
  if (!left || !right) {
    issues.push("A condition measurement was not recorded for both runs.");
    return issues;
  }
  if (!left.capability || !right.capability) issues.push("The measured capability was not recorded for both conditions.");
  else if (left.capability !== right.capability) issues.push("The measured capabilities differ.");
  if (!left.metric || !right.metric) issues.push("The metric was not recorded for both conditions.");
  else if (left.metric !== right.metric) issues.push("The measured metrics differ.");
  if (left.run_id !== before.run_id || right.run_id !== after.run_id) issues.push("A measurement's run ID does not match the selected run.");
  if (left.subject !== before.subject || right.subject !== after.subject) issues.push("A measurement's subject does not match its run.");
  if (left.scope !== before.scope || right.scope !== after.scope) issues.push("A measurement's scope does not match its run.");
  if (!positiveCount(left.n) || !positiveCount(right.n)) issues.push("Evaluated sample sizes were not recorded for both conditions.");
  else if (left.n !== right.n) issues.push("The evaluated sample sizes differ.");
  if (!positiveCount(left.expected_n) || !positiveCount(right.expected_n)) issues.push("Expected condition sample sizes were not recorded for both conditions.");
  else if (left.expected_n !== right.expected_n) issues.push("The expected condition sample sizes differ.");
  if (left.expected_n !== before.n_items || right.expected_n !== after.n_items) issues.push("A condition's expected sample size does not match its run.");
  if (left.complete === false || right.complete === false || (positiveCount(left.n) && positiveCount(left.expected_n) && left.n !== left.expected_n) || (positiveCount(right.n) && positiveCount(right.expected_n) && right.n !== right.expected_n)) issues.push("A condition has missing results.");
  if (typeof left.complete !== "boolean" || typeof right.complete !== "boolean") issues.push("Condition completeness was not recorded for both conditions.");
  if (!left.condition || !right.condition) issues.push("The condition was not recorded for both measurements.");
  else if (baseCondition(left.condition) !== baseCondition(right.condition)) issues.push("The solving conditions differ.");
  return issues;
}

export function validateData(value: unknown): ResearchData {
  if (!value || typeof value !== "object") throw new Error("Unsupported research data. Refresh the published scoreboard export.");
  const data = value as Partial<ResearchData>;
  if (data.schema_version !== 1 || !Array.isArray(data.records) || !Array.isArray(data.runs)
    || !Array.isArray(data.capabilities) || !Array.isArray(data.subjects)) throw new Error("Unsupported research data. Refresh the published scoreboard export.");
  return data as ResearchData;
}
