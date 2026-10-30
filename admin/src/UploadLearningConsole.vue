<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { requestHeaders } from "./evolution";
type Policy = { id: string; version: number; content_hash: string; expert_rules: number; experience_rules: number };
type Observation = { id: string; created_at: string; subtype: string; reference_status: string; reference_source: string; knowledge_origin: string;
  outcome: string; memory_version: number | null; operator_test: boolean; measurements: Record<string, unknown> };
type Cycle = { id: string; status: string; trigger: string; source_count: number; baseline: Policy; candidate: Policy | null;
  registration: Record<string, unknown>; evaluation: { rounds?: { round: number; n: number; baseline_correct: number; candidate_correct: number; gained: number; lost: number }[]; stable_gains?: number };
  decision_reasons: string[]; service_verification: Record<string, unknown>; events: { stage: string; message: string; at: string }[] };
type State = { storage: string; active_memory: Policy | null; worker: { online: boolean; last_seen_at: string | null; mode: string };
  totals: { uploads: number; operator_checks: number; reference_statuses: Record<string, number>; outcomes: Record<string, number> };
  observations: Observation[]; cycles: Cycle[]; budget: Record<string, number> };
const state = ref<State | null>(null);
const error = ref("");
const privateDetails = ref<Record<string, { baseline_payload: Record<string, string[]>; candidate_payload: Record<string, string[]> | null; source_storage: string }>>({});
let timer: ReturnType<typeof setInterval> | undefined;
const label = (s: string) => s.replaceAll("_", " ");
async function refresh() {
  try {
    const response = await fetch("/admin/uploads", { cache: "no-store" });
    if (!response.ok) throw new Error(`Upload learning unavailable (${response.status})`);
    state.value = await response.json(); error.value = "";
  } catch (e) { error.value = e instanceof Error ? e.message : "Could not load the upload learning record"; }
}
async function inspect(id: string) {
  try {
    const response = await fetch(`/api/v1/research/memory_cycles/${id}`, { cache: "no-store", headers: requestHeaders() });
    if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Sign in with your curator account in the learner app to inspect private rule payloads." : "Private candidate details are unavailable.");
    privateDetails.value[id] = await response.json(); error.value = "";
  } catch (e) { error.value = e instanceof Error ? e.message : "Private details unavailable"; }
}
onMounted(() => { refresh(); timer = setInterval(refresh, 10000); });
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>
<template>
  <div class="content uploads-console">
    <div class="page-heading"><div><p class="eyebrow">GMAT CR · E11</p><h1>Uploads → evaluated improvement</h1><p class="subtitle">Blind observations, private local validation and versioned service application.</p></div><button class="button" @click="refresh">Refresh</button></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="state">
      <div class="stats-grid">
        <div class="stat"><p>Learner upload observations</p><strong>{{ state.totals.uploads }}</strong><small>{{ state.totals.operator_checks }} separately labeled operator checks</small></div>
        <div class="stat"><p>Active solving memory</p><strong>v{{ state.active_memory?.version ?? '?' }}</strong><small>{{ state.active_memory?.expert_rules ?? 0 }} reference-derived · {{ state.active_memory?.experience_rules ?? 0 }} usage-derived rules</small></div>
        <div class="stat"><p>Private local evaluator</p><strong>{{ state.worker.online ? 'Online' : 'Waiting' }}</strong><small>{{ state.worker.last_seen_at ?? 'No heartbeat yet' }}</small></div>
        <div class="stat"><p>Recorded cycles</p><strong>{{ state.cycles.length }}</strong><small>Adopted, held and failed outcomes remain visible</small></div>
      </div>
      <section class="panel"><h2>Service and research run independently</h2><p>{{ state.storage }}</p><p>Two solving calls receive question fields only. Reference answers, expert explanations, learner choices and the other solver's response are withheld. Matching AI answers remain estimates.</p><p>New reference mismatches or disagreements can trigger a local review. Three distinct observed questions also trigger a batch check. Without a failure signal, the batch is held without a paid proposal.</p><p v-if="!state.worker.online" class="notice">The learner app continues normally. Candidate evaluation waits until the private local worker is online.</p><p class="notice">At most two paid cycles per day, with a 15-minute cooldown. Each candidate needs two fresh paired passes on at least twelve disjoint source-keyed local validation items, no regressions and a reproduced gain. These pilot checks do not prove 99.9% reliability or learner growth.</p><code v-if="state.active_memory">Active memory hash: {{ state.active_memory.content_hash }}</code><p><a href="/admin#evolution">Inspect the separate verifier policy and service guard ↗</a></p></section>
      <p class="notice">Daily cycles used: {{ state.budget.daily_used ?? 0 }}/{{ state.budget.daily_cycles }} · new observations awaiting the next batch: {{ state.budget.waiting_observations ?? 0 }}. A cooldown or exhausted budget delays research; it does not block learner analysis.</p>
      <section class="panel"><h2>Evidence quality</h2><div class="source-counts"><span v-for="(n, status) in state.totals.reference_statuses" :key="status">{{ label(status) }}: <strong>{{ n }}</strong></span></div><p>Confirmed reference means a separately attested source key. Supplied/extracted references and AI estimates are kept separate. Neither AI votes nor a model-generated explanation creates validation gold.</p></section>
      <section v-for="cycle in state.cycles" :key="cycle.id" class="panel">
        <div class="panel-heading"><div><p class="eyebrow">{{ cycle.id }} · {{ label(cycle.trigger) }}</p><h2>{{ label(cycle.status) }} <span class="scope-badge">v{{ cycle.baseline.version }} → {{ cycle.candidate ? `v${cycle.candidate.version}` : 'candidate pending' }}</span></h2></div><span>{{ cycle.source_count }} observations</span></div>
        <p v-for="reason in cycle.decision_reasons" :key="reason" class="notice">{{ reason }}</p>
        <div v-if="cycle.evaluation.rounds" class="table-wrap"><table><thead><tr><th>Fresh pass</th><th>Items</th><th>Baseline correct</th><th>Candidate correct</th><th>Gained</th><th>Lost</th></tr></thead><tbody><tr v-for="round in cycle.evaluation.rounds" :key="round.round"><td>{{ round.round }}</td><td>{{ round.n }}</td><td>{{ round.baseline_correct }}</td><td>{{ round.candidate_correct }}</td><td>{{ round.gained }}</td><td>{{ round.lost }}</td></tr></tbody></table><p>Reproduced gains on the same item: {{ cycle.evaluation.stable_gains ?? 0 }}. Repeated passes are correlated.</p></div>
        <details><summary>Validation provenance and application proof</summary><dl><template v-for="(value, key) in cycle.registration" :key="key"><dt>{{ key }}</dt><dd><code>{{ value }}</code></dd></template></dl><p>Runtime verification: {{ cycle.service_verification.verified === true ? 'verified' : 'not established' }}</p><code v-if="cycle.candidate">Candidate hash: {{ cycle.candidate.content_hash }}</code></details>
        <button v-if="cycle.candidate && !privateDetails[cycle.id]" class="button small" @click="inspect(cycle.id)">Inspect private rules · curator only</button>
        <details v-if="privateDetails[cycle.id]" open><summary>Private candidate procedures</summary><p>{{ privateDetails[cycle.id].source_storage }}</p><div v-for="(rules, origin) in privateDetails[cycle.id].candidate_payload" :key="origin"><h3>{{ label(String(origin)) }}</h3><ul><li v-for="rule in rules" :key="rule">{{ rule }}</li></ul></div></details>
        <ol><li v-for="(event, index) in cycle.events" :key="index"><strong>{{ label(event.stage) }}</strong> · {{ event.message }} <small>{{ event.at }}</small></li></ol>
      </section>
      <section class="panel"><h2>Recent upload observations</h2><p v-if="!state.observations.length">No GMAT CR uploads have been observed by this version yet. Register a question in Snap to begin.</p><div v-else class="table-wrap"><table><thead><tr><th>Observation</th><th>Type</th><th>Answer evidence</th><th>Outcome</th><th>Applied memory</th><th>Source origin</th></tr></thead><tbody><tr v-for="o in state.observations" :key="o.id"><td>{{ o.id }}<small v-if="o.operator_test">operator check</small></td><td>{{ o.subtype }}</td><td>{{ label(o.reference_status) }}<small>{{ label(o.reference_source) }}</small></td><td>{{ label(o.outcome) }}</td><td>v{{ o.memory_version ?? 'unrecorded' }}</td><td>{{ label(o.knowledge_origin) }}</td></tr></tbody></table></div></section>
    </template>
  </div>
</template>
<style scoped>
.uploads-console>.panel{margin-bottom:24px}.uploads-console p{line-height:1.65}.notice{background:#fff9ed;padding:12px;border-left:3px solid #d6a958}.uploads-console code{overflow-wrap:anywhere}.uploads-console table{width:100%;text-align:left}.uploads-console td,.uploads-console th{padding:12px 8px;border-bottom:1px solid #e2e8ed}.uploads-console td small{display:block;color:#687b8c}.uploads-console .table-wrap{overflow:auto}.uploads-console li{margin:12px 0}.uploads-console li small{display:block;color:#728393}.source-counts{display:flex;flex-wrap:wrap;gap:18px}.uploads-console dl{display:grid;grid-template-columns:150px 1fr;gap:8px}.uploads-console dd{margin:0;min-width:0}@media(max-width:750px){.uploads-console .stats-grid{grid-template-columns:1fr 1fr}.uploads-console dl{grid-template-columns:1fr}.uploads-console .panel-heading{flex-wrap:wrap;gap:12px}}
</style>
