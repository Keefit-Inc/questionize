export interface Capability { id: string; name: string; bar: string; metric: string; unit: string; direction: string }
export interface Qualification { id: string; summary: string; report_url?: string }
export interface Run {
  run_id: string; protocol: string; protocol_version: number; started_at: string; subject: string;
  scope: "full" | "trial"; n_items: number; dataset_id: string; dataset_hash: string;
  split: string; prompts_hash: string; git_sha: string; models: Record<string, string>;
  judge: Record<string, unknown>; memory: { hash: string; lessons: number } | null;
  baseline_run: string | null; note: string; capabilities: string[]; measured_capabilities: string[];
  qualifications?: Qualification[];
}
export interface Comparison { b?: number; c?: number; p?: number; n?: number; baseline_accuracy?: number; diff_ci95?: [number, number] }
export interface Measurement {
  run_id: string; capability: string; subject: string; condition: string; scope: "full" | "trial";
  metric: string; value: number; n: number | null; ci95: [number, number] | null;
  expected_n: number | null; complete: boolean | null; calls?: number; ece?: number;
  vs_B0?: Comparison; vs_baseline?: Comparison;
}
export interface ResearchData {
  schema_version: number; updated_at: string | null; capabilities: Capability[];
  subjects: string[]; runs: Run[]; records: Measurement[];
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
  if (!["full", "trial"].includes(before.scope) || !["full", "trial"].includes(after.scope)) issues.push("Evaluation scope was not recorded for both runs.");
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
