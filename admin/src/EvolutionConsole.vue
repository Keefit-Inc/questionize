<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { timestamp } from "./research";
import { commitUrl, isInFlight, loadEvolution, modeLabel, percent, points, readable, STAGES, stageState, startEvolution, STATUS_LABELS, type EvolutionData } from "./evolution";

const emit = defineEmits<{ completed: [] }>();
const data = ref<EvolutionData | null>(null);
const error = ref("");
const loading = ref(false);
const starting = ref(false);
const selectedId = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
let disposed = false;
let previousPending = new Map<string, boolean>();

const cycles = computed(() => [...(data.value?.cycles ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at)));
const selected = computed(() => cycles.value.find((cycle) => cycle.id === selectedId.value) ?? cycles.value[0]);
const codeRevision = computed(() => selected.value?.code_revision ?? selected.value?.code_sha);
const inProgress = computed(() => cycles.value.some(isInFlight));
const activePolicy = computed(() => data.value?.active_policy);
const canStart = computed(() => data.value?.operator.curator && !!activePolicy.value && data.value.automation.readiness !== "daily_proposal_limit_reached" && !inProgress.value && !starting.value && !loading.value);
const adopted = computed(() => cycles.value.filter((cycle) => cycle.status === "adopted").length);
const held = computed(() => cycles.value.filter((cycle) => cycle.status === "held").length);
const cadence = computed(() => {
  const seconds = data.value?.automation.cooldown_seconds ?? 0;
  return seconds >= 86400 ? `${(seconds / 86400).toFixed(0)} day` : seconds >= 3600 ? `${(seconds / 3600).toFixed(0)} hours` : `${(seconds / 60).toFixed(0)} minutes`;
});

async function refresh() {
  clearTimeout(timer);
  if (loading.value || disposed) return;
  loading.value = true;
  try {
    const next = await loadEvolution();
    if (disposed) return;
    const completed = next.cycles.some((cycle) => previousPending.get(cycle.id) === true && !isInFlight(cycle));
    previousPending = new Map(next.cycles.map((cycle) => [cycle.id, isInFlight(cycle)]));
    data.value = next;
    if (!next.cycles.some((cycle) => cycle.id === selectedId.value)) selectedId.value = cycles.value[0]?.id ?? "";
    error.value = "";
    if (completed) emit("completed");
  } catch (e) {
    if (!disposed) error.value = e instanceof Error ? e.message : "Couldn't load evolution status.";
  } finally {
    loading.value = false;
    if (!disposed && inProgress.value && !error.value) timer = setTimeout(refresh, 4000);
  }
}

async function start() {
  if (!canStart.value) return;
  starting.value = true; error.value = "";
  try {
    const id = await startEvolution();
    if (id) selectedId.value = id;
    await refresh();
  } catch (e) { error.value = e instanceof Error ? e.message : "Couldn't start the cycle."; }
  finally { starting.value = false; }
}

onMounted(refresh);
onUnmounted(() => { disposed = true; clearTimeout(timer); });
</script>

<template>
  <div class="content evolution-view">
    <div class="page-heading">
      <div><p class="eyebrow">GMAT CR · C3.1 · VERIFIED POLICY EVOLUTION</p><h1>From evidence to service.</h1><p class="subtitle">Generate a bounded candidate, compare it with the active policy, and keep the decision and service evidence.</p></div>
      <button class="button" :disabled="loading" @click="refresh">↻ {{ loading ? "Refreshing…" : "Refresh status" }}</button>
    </div>
    <div class="evidence-boundary"><strong>Development decision replay</strong><p>This cycle tests a Judge routing policy against recorded Solver and Judge decisions. It is not a new blind model evaluation, model fine-tuning, or evidence of learner growth. No official question text is shown here.</p></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="!data && loading" class="empty">Reading the live evolution registry…</p>
    <template v-if="data">
      <div class="evolution-stats">
        <section class="panel active-policy"><p class="eyebrow">ACTIVE IN SERVICE</p><h2>{{ activePolicy ? `Policy v${activePolicy.version}` : "No active policy" }}</h2><strong>{{ modeLabel(activePolicy) }}</strong><code>{{ activePolicy?.content_hash ?? 'A baseline policy must be configured.' }}</code><small v-if="activePolicy?.activated_at">Activated {{ timestamp(activePolicy.activated_at) }}</small></section>
        <section class="panel cycle-counts"><p class="eyebrow">DECISIONS RETAINED</p><div><span><strong>{{ adopted }}</strong>adopted</span><span><strong>{{ held }}</strong>held</span><span><strong>{{ cycles.length }}</strong>total cycles</span></div><small>Held candidates do not change the active service policy.</small></section>
        <section class="panel automatic-batches"><p class="eyebrow">USAGE-DRIVEN BATCHES</p><h2>{{ data.automation.enabled ? 'Enabled' : 'Not enabled' }}</h2><p>{{ data.automation.eligible_sources }} / {{ data.automation.min_trusted_sources }} trusted sources · {{ data.automation.new_rated_attempts }} / {{ data.automation.min_rated_attempts }} new rated answers</p><small>{{ readable(data.automation.readiness) }} · minimum interval {{ cadence }}</small><small v-if="data.automation.daily_limit != null">Proposal budget: {{ data.automation.daily_used ?? 0 }} / {{ data.automation.daily_limit }} today</small></section>
      </div>

      <section class="panel cycle-control">
        <div><h2>Run the next candidate</h2><p v-if="data.operator.curator">Signed in as {{ data.operator.handle }}. This starts a Meta candidate-generation call and a recorded comparison against the active policy.</p><p v-else>Public aggregate view. <a href="/me">Sign in with your curator account</a> in Questionize, then refresh to operate a cycle.</p></div>
        <button v-if="data.operator.curator" class="button primary" :disabled="!canStart" @click="start">{{ starting ? 'Starting…' : inProgress ? 'Cycle in progress' : 'Generate and evaluate candidate' }}</button>
      </section>

      <div class="evolution-layout">
        <section class="panel cycle-list"><div class="panel-heading"><div><p class="eyebrow">LIVE REGISTRY</p><h2>Evolution cycles <span class="count">{{ cycles.length }}</span></h2></div><span v-if="inProgress && !error" class="live-indicator" role="status">● Updating</span></div>
          <p v-if="!cycles.length" class="empty">No cycles yet. A configured benchmark and a curator-triggered run, or enough eligible usage evidence, will start the first cycle.</p>
          <button v-for="cycle in cycles" :key="cycle.id" :class="['cycle-row', { chosen: selected?.id === cycle.id }]" :aria-pressed="selected?.id === cycle.id" @click="selectedId = cycle.id"><span><strong>{{ cycle.id }}</strong><small>{{ readable(cycle.trigger) }} · {{ timestamp(cycle.created_at) }}</small></span><span :class="['cycle-status', cycle.status]">{{ STATUS_LABELS[cycle.status] }}</span></button>
        </section>

        <section v-if="selected" class="panel cycle-detail">
          <div class="panel-heading"><div><p class="eyebrow">RECORDED PROCESS</p><h2>Candidate {{ selected.candidate_policy ? `v${selected.candidate_policy.version}` : 'pending' }}</h2></div><span :class="['cycle-status', selected.status]">{{ STATUS_LABELS[selected.status] }}</span></div>
          <ol class="stage-track" aria-label="Evolution stages"><li v-for="stage in STAGES" :key="stage.id" :class="stageState(selected, stage.id)"><span>{{ stageState(selected, stage.id) === 'complete' ? '✓' : STAGES.indexOf(stage) + 1 }}</span>{{ stage.label }}</li></ol>
          <div class="policy-comparison"><div><small>BASELINE · {{ selected.baseline_policy ? `v${selected.baseline_policy.version}` : 'not recorded' }}</small><strong>{{ modeLabel(selected.baseline_policy) }}</strong><code>{{ selected.baseline_policy?.content_hash ?? '—' }}</code></div><span>→</span><div><small>CANDIDATE · {{ selected.candidate_policy ? `v${selected.candidate_policy.version}` : 'pending' }}</small><strong>{{ modeLabel(selected.candidate_policy) }}</strong><code>{{ selected.candidate_policy?.content_hash ?? '—' }}</code></div></div>
          <div v-if="selected.proposal" class="proposal-notes"><h3>Candidate hypothesis</h3><p>{{ selected.proposal.hypothesis }}</p><p class="muted">{{ selected.proposal.reason }}</p><small>{{ selected.proposal.model }} · {{ selected.proposal.logical_calls }} generation call<template v-if="selected.proposal.duration_seconds != null"> · {{ selected.proposal.duration_seconds.toFixed(1) }} s</template></small></div>
          <template v-if="selected.evaluation">
            <div class="evaluation-values"><div><small>BASELINE</small><strong>{{ selected.evaluation.baseline.correct }} / {{ selected.evaluation.baseline.n }}</strong><span>{{ percent(selected.evaluation.baseline.accuracy) }}</span></div><div><small>CANDIDATE</small><strong>{{ selected.evaluation.candidate.correct }} / {{ selected.evaluation.candidate.n }}</strong><span>{{ percent(selected.evaluation.candidate.accuracy) }}</span></div><div><small>OBSERVED CHANGE</small><strong>{{ points(selected.evaluation.comparison.delta) }}</strong><span>{{ selected.evaluation.comparison.gained }} gained · {{ selected.evaluation.comparison.lost }} lost</span></div></div>
            <p v-if="selected.evaluation.comparison.diff_ci95" class="interval-note">Recorded paired 95% interval: {{ points(selected.evaluation.comparison.diff_ci95[0]) }} to {{ points(selected.evaluation.comparison.diff_ci95[1]) }}<template v-if="selected.evaluation.comparison.mcnemar_p != null"> · McNemar p = {{ selected.evaluation.comparison.mcnemar_p }}</template></p>
            <div :class="['decision-box', { passed: selected.evaluation.gate.passed }]"><strong>{{ selected.evaluation.gate.passed ? 'Regression gate passed' : 'Regression gate not passed' }}</strong><p>This is a bounded software-policy gate, not a claim of statistically established general model improvement.</p><p v-if="selected.criteria" class="registered-gate">Frozen gate: at least {{ selected.criteria.min_cases }} cases, {{ selected.criteria.min_improvements }} improvement, at most {{ selected.criteria.max_regressions }} regressions. Standard decisions must remain unchanged.</p><ul><li v-for="(reason, index) in selected.evaluation.gate.reasons" :key="index">{{ readable(reason) }}</li><li v-if="selected.evaluation.comparison.standard_changes != null">Standard decisions changed: {{ selected.evaluation.comparison.standard_changes }}</li><li v-if="selected.evaluation.comparison.standard_regressions != null">Standard-case regressions: {{ selected.evaluation.comparison.standard_regressions }}</li><li v-if="selected.evaluation.comparison.except_gained != null">EXCEPT cases improved: {{ selected.evaluation.comparison.except_gained }}</li></ul></div>
          </template>
          <div v-if="selected.decision_reasons.length" class="decision-reasons"><h3>Decision grounds</h3><ul><li v-for="(reason, index) in selected.decision_reasons" :key="index">{{ readable(reason) }}</li></ul></div>
          <div :class="['service-evidence', { verified: selected.service_verification?.verified }]"><strong>{{ selected.service_verification?.verified ? 'Service application verified' : selected.status === 'held' ? 'Active service policy preserved' : 'Service application not yet verified' }}</strong><template v-if="selected.service_verification"><p v-if="selected.service_verification.policy_id">The service reported policy {{ selected.service_verification.policy_id }}.</p><code v-if="selected.service_verification.policy_hash">{{ selected.service_verification.policy_hash }}</code><small v-if="selected.service_verification.selection_source">Selected from {{ readable(selected.service_verification.selection_source) }}</small><small v-if="selected.service_verification.wired_paths?.length">Connected verification paths: {{ selected.service_verification.wired_paths.map(readable).join(' · ') }}</small><small v-if="selected.service_verification.chosen_answer">Probe decision {{ selected.service_verification.chosen_answer }}<template v-if="selected.service_verification.expected_answer"> · expected {{ selected.service_verification.expected_answer }}</template></small><small v-if="selected.service_verification.failure">Verification stopped: {{ selected.service_verification.failure }}</small><small v-if="selected.service_verification.checked_at">Checked {{ timestamp(selected.service_verification.checked_at) }}</small></template><p v-else-if="selected.status === 'held'">This candidate was not applied. The active version above remains the operating policy.</p><p v-else>Adoption is verified against the service policy interpreter; saving a candidate alone does not count as service application.</p></div>
          <details class="cycle-provenance"><summary>Benchmark and source provenance</summary><dl><dt>Cycle</dt><dd>{{ selected.id }}</dd><dt>Trigger</dt><dd>{{ readable(selected.trigger) }}</dd><template v-if="selected.sources"><dt>Batch evidence</dt><dd>{{ selected.sources.trusted_sources }} trusted sources · {{ selected.sources.new_rated_attempts }} rated answers</dd></template><dt>Benchmark</dt><dd>{{ selected.benchmark?.id ?? 'Not configured' }}<code>{{ selected.benchmark?.hash }}</code></dd><dt>Evidence kind</dt><dd>{{ selected.benchmark ? readable(selected.benchmark.kind) : '—' }} · {{ selected.benchmark ? readable(selected.benchmark.purpose) : '—' }}</dd><dt>Cases</dt><dd>{{ selected.benchmark?.n ?? '—' }}</dd><dt>Parent dataset</dt><dd><code>{{ selected.benchmark?.parent_dataset_hash ?? 'Not recorded' }}</code></dd><template v-if="codeRevision"><dt>Code</dt><dd><a v-if="commitUrl(codeRevision)" :href="commitUrl(codeRevision)!" target="_blank" rel="noreferrer">{{ codeRevision.slice(0, 12) }} ↗</a><code v-else>{{ codeRevision }}</code></dd></template></dl></details>
          <div class="event-history"><h3>Event timeline</h3><ol><li v-for="(event, index) in selected.events" :key="index"><span class="event-dot" /><div><strong>{{ readable(event.stage) }}</strong><p>{{ event.message }}</p><small>{{ timestamp(event.created_at) }}</small></div></li><li v-if="!selected.events.length" class="empty">No stage events recorded yet.</li></ol></div>
        </section>
      </div>
      <footer><span>Live state from PostgreSQL. Refresh reads current status; generating a candidate is a separate operation.</span><span>GMAT CR · C3.1 · bounded Judge policy</span></footer>
    </template>
  </div>
</template>

<style scoped>
.evidence-boundary { padding:15px 18px; margin-bottom:20px; border:1px solid #dfdacd; background:#fffaf0; border-radius:8px; color:#8c7549; font-size:11px; line-height:1.7; }
.evidence-boundary p { margin:5px 0 0; }
.evolution-stats { display:grid; grid-template-columns:1fr 1fr 1.1fr; gap:16px; }
.evolution-stats .panel { padding:21px; }
.evolution-stats h2 { margin-bottom:13px; }
.active-policy>strong { display:block; font-size:12px; margin-bottom:6px; }
.active-policy small,.evolution-stats small { display:block; color:#8b98a4; font-size:10px; line-height:1.7; margin-top:8px; }
.active-policy code { font-size:10px; }
.cycle-counts>div { display:flex; gap:20px; margin:20px 0 13px; }
.cycle-counts>div>span { color:#82919e; font-size:10px; }
.cycle-counts strong { display:block; color:#344e60; font:750 26px 'Manrope',sans-serif; margin-bottom:7px; }
.automatic-batches p { font-size:11px; line-height:1.8; color:#697e8e; }
.cycle-control { display:flex; gap:20px; align-items:center; justify-content:space-between; padding:21px 25px; }
.cycle-control p { font-size:11px; line-height:1.7; margin:7px 0 0; color:#82919e; max-width:650px; }
.button.primary { background:#276c5b; color:#fff; border-color:#276c5b; }
.evolution-layout { display:grid; grid-template-columns:minmax(245px,.7fr) minmax(0,1.5fr); gap:21px; align-items:start; }
.cycle-list .panel-heading { padding:21px 19px; }
.live-indicator { color:#33856c; font-size:10px; white-space:nowrap; }
.cycle-row { width:100%; display:flex; gap:12px; align-items:center; justify-content:space-between; text-align:left; border:0; border-top:1px solid #edf0f3; background:white; padding:18px; color:#597184; }
.cycle-row:hover,.cycle-row.chosen { background:#f1f7f5; }
.cycle-row>span:first-child { min-width:0; }
.cycle-row strong { display:block; max-width:180px; overflow:hidden; text-overflow:ellipsis; font:600 11px ui-monospace,monospace; }
.cycle-row small { display:block; color:#91a0aa; font-size:9px; line-height:1.7; margin-top:6px; }
.cycle-status { display:inline-block; padding:5px 7px; border:1px solid #e1e7ed; border-radius:5px; color:#7a8d9c; background:#f6f8fa; font-size:9px; font-weight:600; white-space:nowrap; }
.cycle-status.adopted { color:#277e61; background:#eef8f1; border-color:#d6ebdd; }
.cycle-status.held { color:#9c7939; background:#fff9eb; border-color:#eee2c8; }
.cycle-status.failed { color:#a65c4e; background:#fff1ec; border-color:#f0d8ce; }
.cycle-status.generating,.cycle-status.evaluating,.cycle-status.activating,.cycle-status.queued { color:#426da1; background:#f0f5fe; border-color:#dce7f7; }
.stage-track { display:grid; grid-template-columns:repeat(5,1fr); list-style:none; padding:13px 25px 20px; margin:0; gap:5px; }
.stage-track li { color:#a0adb6; font-size:9px; text-align:center; }
.stage-track li>span { display:grid; place-content:center; width:26px; height:26px; margin:0 auto 8px; border-radius:50%; border:1px solid #e0e6eb; background:#fafbfc; font-size:10px; }
.stage-track .complete { color:#3b876d; }.stage-track .complete>span { background:#edf7f1; border-color:#cce5d7; }
.stage-track .current { color:#4678ac; }.stage-track .current>span { background:#eef4fe; border-color:#b9cde9; }
.stage-track .held { color:#a07a38; }.stage-track .held>span { background:#fff7e8; border-color:#ead9b6; }
.policy-comparison { display:flex; gap:16px; align-items:center; margin:0 25px; padding:18px; border:1px solid #e5ebf0; border-radius:7px; background:#fafcfd; }
.policy-comparison>div { flex:1; min-width:0; }.policy-comparison>span { color:#a4b1ba; }
.policy-comparison small { color:#96a4af; display:block; font-size:8px; letter-spacing:.6px; margin-bottom:8px; }
.policy-comparison strong { display:block; font-size:12px; color:#526f7f; line-height:1.6; }
.proposal-notes { padding:23px 25px 5px; }.proposal-notes p { font-size:12px; line-height:1.8; color:#526e7e; }.proposal-notes p.muted { color:#8899a6; font-size:11px; }
.proposal-notes small,.service-evidence small { display:block; font-size:10px; color:#8e9da8; margin-top:7px; }
h3 { font-size:12px; font-weight:700; letter-spacing:0; color:#577081; }
.evaluation-values { display:grid; grid-template-columns:1fr 1fr 1.15fr; margin:25px; gap:16px; }
.evaluation-values small { display:block; font-size:8px; color:#98a5af; letter-spacing:.7px; margin-bottom:9px; }
.evaluation-values strong { display:block; font:750 23px 'Manrope',sans-serif; color:#385c6c; letter-spacing:-.5px; }
.evaluation-values span { display:block; color:#8e9eaa; font-size:10px; margin-top:8px; }
.interval-note { margin:0 25px 17px; color:#94a1ac; font-size:10px; line-height:1.8; }
.decision-box,.service-evidence { margin:18px 25px; padding:15px; background:#fffaf0; border:1px solid #ede2c9; border-radius:7px; color:#927945; font-size:11px; line-height:1.8; }
.decision-box.passed,.service-evidence.verified { color:#4a7a66; border-color:#d9e9df; background:#f1f8f4; }
.decision-box p,.service-evidence p { margin:5px 0; }.decision-box ul,.decision-reasons ul { padding-left:17px; margin:8px 0 0; }
.decision-reasons { margin:22px 25px; font-size:11px; color:#7d8f9d; line-height:1.8; }
.cycle-provenance { margin:22px 25px; font-size:11px; color:#748a99; }
.cycle-provenance summary { cursor:pointer; font-weight:600; }.cycle-provenance dl { padding:20px 0 0; }
.event-history { margin:25px; border-top:1px solid #edf0f3; padding-top:20px; }
.event-history ol { list-style:none; padding:0; margin:15px 0 0; }.event-history li { display:flex; gap:13px; position:relative; padding:0 0 22px; }
.event-history li:not(:last-child)::before { content:''; position:absolute; left:4px; top:8px; bottom:0; width:1px; background:#e4eaf0; }
.event-dot { width:9px; height:9px; border-radius:50%; background:#99baad; border:2px solid #e7f1eb; margin-top:3px; flex:none; z-index:1; }
.event-history strong { color:#5f7a89; font-size:10px; text-transform:capitalize; }.event-history p { margin:5px 0; font-size:11px; line-height:1.8; color:#8a9ba7; }.event-history small { font-size:9px; color:#a3afb8; }
@media(max-width:1150px) { .evolution-layout { grid-template-columns:1fr; }.evolution-stats { gap:12px; }.evolution-stats .panel { padding:17px; }.cycle-row strong { max-width:none; }.cycle-control { align-items:flex-start; } }
@media(max-width:760px) { .evolution-stats { grid-template-columns:1fr; gap:0; }.evolution-stats .panel { margin-bottom:12px; padding:19px; }.cycle-control { display:block; padding:19px; }.cycle-control .button { margin-top:15px; white-space:normal; text-align:center; width:100%; }.cycle-counts>div { gap:38px; }.policy-comparison { margin-inline:18px; padding:13px; gap:10px; }.policy-comparison strong { font-size:11px; }.policy-comparison code { font-size:8px; }.stage-track { padding-inline:16px; }.evaluation-values { margin:23px 18px; gap:10px; }.evaluation-values strong { font-size:18px; }.evaluation-values small { font-size:7px; }.evaluation-values span { font-size:9px; }.proposal-notes { padding-inline:18px; }.decision-box,.service-evidence,.event-history,.cycle-provenance,.decision-reasons { margin-inline:18px; }.interval-note { margin-inline:18px; }.cycle-row strong { max-width:180px; }.evidence-boundary { font-size:10px; }.event-history li { padding-bottom:20px; } }
</style>
