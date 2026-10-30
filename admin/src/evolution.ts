export type CycleStatus = "queued" | "generating" | "evaluating" | "activating" | "adopted" | "held" | "failed";
export interface PolicyVersion {
  id: string;
  version: number;
  content_hash: string;
  payload: { except_mode: "legacy" | "abstain" };
  activated_at?: string | null;
  cycle_id?: string | null;
}
export interface Benchmark {
  id: string;
  hash: string;
  n: number;
  kind: string;
  purpose: string;
  parent_dataset_hash?: string;
}
export interface Score { n: number; correct: number; accuracy: number; ci95?: [number, number] | null }
export interface CycleEvaluation {
  baseline: Score;
  candidate: Score;
  comparison: {
    gained: number; lost: number; delta: number;
    mcnemar_p?: number | null; diff_ci95?: [number, number] | null;
    standard_changes?: number; standard_regressions?: number; except_gained?: number;
  };
  gate: { passed: boolean; reasons: string[] };
}
export interface CycleEvent {
  stage: string;
  message: string;
  created_at: string;
  data?: Record<string, unknown>;
}
export interface EvolutionCycle {
  id: string;
  status: CycleStatus;
  trigger: string;
  created_at: string;
  updated_at: string;
  baseline_policy: PolicyVersion | null;
  candidate_policy: PolicyVersion | null;
  benchmark: Benchmark | null;
  proposal: { reason: string; hypothesis: string; model: string; logical_calls: number; duration_seconds?: number } | null;
  evaluation: CycleEvaluation | null;
  decision_reasons: string[];
  service_verification: {
    verified: boolean; policy_id?: string; policy_hash?: string;
    chosen_answer?: string; expected_answer?: string; checked_at?: string;
    selection_source?: string; application_paths?: string[]; wired_paths?: string[]; failure?: string;
  } | null;
  events: CycleEvent[];
  code_sha?: string;
  code_revision?: string;
  sources?: { trusted_sources: number; new_rated_attempts: number };
  criteria?: { min_cases: number; min_improvements: number; max_regressions: number; daily_limit?: number };
  protocol?: string;
}
export interface EvolutionData {
  schema_version: number;
  scope: { subject: string; level: string; capability: string; policy_kind: string };
  active_policy: PolicyVersion | null;
  automation: {
    enabled: boolean; min_trusted_sources: number; min_rated_attempts: number;
    cooldown_seconds: number; eligible_sources: number; new_rated_attempts: number;
    readiness: string; daily_limit?: number; daily_used?: number;
  };
  cycles: EvolutionCycle[];
  operator: { authenticated: boolean; curator: boolean; handle?: string };
}

export const ACTIVE_STATUSES: CycleStatus[] = ["queued", "generating", "evaluating", "activating"];
export const STATUS_LABELS: Record<CycleStatus, string> = {
  queued: "Queued", generating: "Generating candidate", evaluating: "Comparing policies",
  activating: "Verifying service application", adopted: "Adopted", held: "Held", failed: "Failed",
};
export const STAGES = [
  { id: "queued", label: "Evidence" },
  { id: "generating", label: "Candidate" },
  { id: "evaluating", label: "Comparison" },
  { id: "decision", label: "Decision" },
  { id: "service", label: "Service" },
];
export const isActive = (status: CycleStatus) => ACTIVE_STATUSES.includes(status);
export const isInFlight = (cycle: EvolutionCycle) => isActive(cycle.status) || (cycle.status === "adopted" && cycle.service_verification == null);
export const modeLabel = (policy: PolicyVersion | null | undefined) => !policy ? "Not configured"
  : policy.payload.except_mode === "abstain" ? "Abstain on EXCEPT" : "Legacy subtype routing";
export const percent = (n: number | null | undefined) => n == null ? "—" : `${(n * 100).toFixed(2)}%`;
export const points = (n: number | null | undefined) => n == null ? "—" : `${n > 0 ? "+" : ""}${(n * 100).toFixed(2)} pp`;
export const readable = (value: string) => value.replace(/_/g, " ");
export const commitUrl = (revision: string | undefined) => revision && /^[0-9a-f]{7,40}$/.test(revision)
  ? `https://github.com/Keefit-Inc/questionize/commit/${revision}` : null;

export function stageState(cycle: EvolutionCycle, id: string): "complete" | "current" | "pending" | "held" {
  if (id === "queued") return cycle.status === "queued" ? "current" : "complete";
  if (id === "generating") return cycle.proposal || cycle.candidate_policy ? "complete" : cycle.status === "generating" ? "current" : "pending";
  if (id === "evaluating") return cycle.evaluation ? "complete" : cycle.status === "evaluating" ? "current" : "pending";
  if (id === "decision") return ["activating", "adopted", "held", "failed"].includes(cycle.status) ? ["activating", "adopted"].includes(cycle.status) ? "complete" : "held" : "pending";
  return cycle.service_verification?.verified ? "complete" : ["activating", "adopted"].includes(cycle.status) ? "current" : "pending";
}

export function validateEvolution(value: unknown): EvolutionData {
  if (!value || typeof value !== "object") throw new Error("Evolution data is unavailable.");
  const data = value as Partial<EvolutionData>;
  if (data.schema_version !== 1 || !data.scope || !data.automation || !data.operator || !Array.isArray(data.cycles)) {
    throw new Error("Unsupported evolution data. The console and service need the same release.");
  }
  return data as EvolutionData;
}

export function requestHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem("questionize.token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch { return {}; }
}

export async function loadEvolution(): Promise<EvolutionData> {
  const response = await fetch("/admin/cycles", { cache: "no-store", headers: requestHeaders() });
  if (!response.ok) throw new Error(`Evolution data is unavailable (${response.status}). Try Refresh after the service is ready.`);
  return validateEvolution(await response.json());
}

export async function startEvolution(): Promise<string | null> {
  const response = await fetch("/api/v1/research/cycles", { method: "POST", headers: { ...requestHeaders(), "Content-Type": "application/json" }, body: "{}" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = response.status === 401 ? "Sign in with your curator account in the learner app, then refresh this console."
      : response.status === 403 ? "Only a curator can start a paid candidate evaluation."
      : typeof body.message === "string" ? body.message : typeof body.error === "string" ? readable(body.error) : `Couldn't start the cycle (${response.status}).`;
    throw new Error(message);
  }
  return body.id ?? body.cycle_id ?? body.cycle?.id ?? null;
}
