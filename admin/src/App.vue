<script setup lang="ts">
import { computed, onMounted, ref, watchEffect } from "vue";
import { GROUPS, baseCondition, comparisonIssues, comparisonView, measurements, percentage, shortId, subjectName, timestamp, validateData, type Measurement, type ResearchData } from "./research";
import EvolutionConsole from "./EvolutionConsole.vue";
import EvidenceConsole from "./EvidenceConsole.vue";
import UploadLearningConsole from "./UploadLearningConsole.vue";

const view = ref<"research" | "evolution" | "evidence" | "uploads">(window.location.hash === "#uploads" ? "uploads" : window.location.hash === "#evolution" ? "evolution" : window.location.hash === "#evidence" ? "evidence" : "research");
const data = ref<ResearchData | null>(null);
const error = ref("");
const loading = ref(false);
const subject = ref("CR");
const group = ref("C3");
const capability = ref("C3.1");
const scope = ref("full");
const condition = ref("all");
const selectedRun = ref("");
const beforeId = ref("");
const afterId = ref("");
const compareCondition = ref("B0");
const COLORS: Record<string, string> = { B0: "#6f7d8c", B1: "#3d6bdc", "B0+M": "#ce7847", "B1+M": "#218a78" };
const color = (name: string) => COLORS[name] ?? "#8a61b6";
const capabilities = computed(() => data.value?.capabilities.filter((c) => c.id.split(".")[0] === group.value) ?? []);
const selectedCapability = computed(() => data.value?.capabilities.find((c) => c.id === capability.value));
const records = computed(() => data.value ? measurements(data.value, subject.value, capability.value, scope.value, condition.value) : []);
const runs = computed(() => data.value?.runs.filter((run) => run.subject === subject.value && run.capabilities.includes(capability.value) && (scope.value === "all" || run.scope === scope.value)) ?? []);
const runMap = computed(() => new Map(data.value?.runs.map((run) => [run.run_id, run])));
const qualifications = computed(() => [...new Map(runs.value.flatMap((run) => run.qualifications ?? []).map((item) => [item.id, item])).values()]);
const series = computed(() => [...new Set(records.value.map((record) => record.condition))]);
const conditions = computed(() => [...new Set(data.value?.records.filter((record) => record.subject === subject.value && record.capability === capability.value).map((record) => record.condition))].sort());
const measuredGroups = computed(() => new Set(data.value?.records.filter((record) => record.subject === subject.value && record.scope === "full").map((record) => record.capability.split(".")[0])));
const groupMeasured = (id: string) => measuredGroups.value.has(id);
const metricCount = computed(() => new Set(data.value?.records.filter((record) => record.subject === subject.value && record.scope === "full").map((record) => record.capability)).size);
const currentRecords = computed(() => {
  const latest = new Map<string, Measurement>();
  for (const record of records.value) {
    const previous = latest.get(record.condition);
    if (!previous || (runMap.value.get(record.run_id)?.started_at ?? "") > (runMap.value.get(previous.run_id)?.started_at ?? "")) latest.set(record.condition, record);
  }
  return [...latest.values()];
});
const chartRuns = computed(() => [...new Set(records.value.map((record) => record.run_id))].sort((a, b) => (runMap.value.get(a)?.started_at ?? "").localeCompare(runMap.value.get(b)?.started_at ?? "")));
const x = (record: Measurement) => {
  const index = chartRuns.value.indexOf(record.run_id);
  return 82 + (chartRuns.value.length > 1 ? index / (chartRuns.value.length - 1) * 620 : 310) + (series.value.indexOf(record.condition) - (series.value.length - 1) / 2) * 8;
};
const y = (value: number) => 232 - Math.min(1, Math.max(0, value)) * 195;
const path = (name: string) => records.value.filter((record) => record.condition === name).sort((a, b) => x(a) - x(b)).map((record) => `${x(record)},${y(record.value)}`).join(" ");
const sortedRecords = computed(() => [...records.value].sort((a, b) => (runMap.value.get(b.run_id)?.started_at ?? "").localeCompare(runMap.value.get(a.run_id)?.started_at ?? "") || a.condition.localeCompare(b.condition)));
const detail = computed(() => runMap.value.get(selectedRun.value));
const before = computed(() => runMap.value.get(beforeId.value));
const after = computed(() => runMap.value.get(afterId.value));
const comparisonConditions = computed(() => [...new Set(records.value.map((record) => baseCondition(record.condition)))]);
const left = computed(() => records.value.find((record) => record.run_id === beforeId.value && baseCondition(record.condition) === compareCondition.value));
const right = computed(() => records.value.find((record) => record.run_id === afterId.value && baseCondition(record.condition) === compareCondition.value));
const issues = computed(() => before.value && after.value ? comparisonIssues(before.value, after.value, left.value, right.value) : []);
const comparison = computed(() => comparisonView(before.value, after.value, left.value, right.value));
const difference = computed(() => comparison.value.difference);
const paired = computed(() => comparison.value.paired);

function showCapability(id: string) {
  group.value = id;
  view.value = "research";
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
}

function showEvolution() {
  view.value = "evolution";
  window.history.replaceState(null, "", "#evolution");
}
function showEvidence() {
  view.value = "evidence";
  window.history.replaceState(null, "", "#evidence");
}
function showUploads() { view.value = "uploads"; window.history.replaceState(null, "", "#uploads"); }

watchEffect(() => {
  if (capabilities.value.length && !capabilities.value.some((c) => c.id === capability.value)) capability.value = capabilities.value[0].id;
  if (condition.value !== "all" && !conditions.value.includes(condition.value)) condition.value = "all";
  if (!runs.value.length) {
    selectedRun.value = "";
    beforeId.value = "";
    afterId.value = "";
  } else {
    if (!runs.value.some((run) => run.run_id === selectedRun.value)) selectedRun.value = runs.value.at(-1)!.run_id;
    if (!runs.value.some((run) => run.run_id === afterId.value)) afterId.value = runs.value.at(-1)!.run_id;
    const target = runMap.value.get(afterId.value);
    if (!runs.value.some((run) => run.run_id === beforeId.value) || beforeId.value === afterId.value) beforeId.value = runs.value.find((run) => run.run_id === target?.baseline_run)?.run_id ?? runs.value[0]?.run_id ?? "";
  }
  if (!comparisonConditions.value.length) compareCondition.value = "";
  else if (!comparisonConditions.value.includes(compareCondition.value)) compareCondition.value = comparisonConditions.value[0];
});

async function refresh() {
  loading.value = true; error.value = "";
  try {
    const response = await fetch("/admin/data", { cache: "no-store" });
    if (!response.ok) throw new Error(`Research data is unavailable (${response.status}).`);
    data.value = validateData(await response.json());
    if (!data.value.subjects.includes(subject.value)) subject.value = data.value.subjects[0] ?? "CR";
  } catch (e) { error.value = e instanceof Error ? e.message : "Couldn't load the research record."; }
  finally { loading.value = false; }
}
function download() {
  const blob = new Blob([JSON.stringify({ subject: subject.value, capability: capability.value, records: records.value, runs: runs.value }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob); const link = document.createElement("a");
  link.href = url; link.download = `questionize-${subject.value}-${capability.value}.json`; link.click(); URL.revokeObjectURL(url);
}
onMounted(refresh);
</script>

<template>
  <div class="console">
    <aside class="sidebar">
      <a class="brand" href="/admin"><span class="brand-mark">Q<span>↗</span></span><span>questionize<small>RESEARCH CONSOLE</small></span></a>
      <div class="workspace"><span class="status-dot" /> Research workspace <span class="workspace-tag">v1</span></div>
      <p class="nav-label">CAPABILITIES</p>
      <nav aria-label="Capabilities">
        <button v-for="item in GROUPS" :key="item.id" :class="['nav-item', { active: view === 'research' && group === item.id }]" :aria-pressed="view === 'research' && group === item.id" @click="showCapability(item.id)">
          <span class="cap-id">{{ item.id }}</span><span>{{ item.name }}<small>{{ item.detail }}</small></span><span :class="['measure-dot', { measured: groupMeasured(item.id) }]" :title="groupMeasured(item.id) ? 'Has full evaluation results' : 'Not measured yet'" />
        </button>
      </nav>
      <button :class="['workflow-nav', { active: view === 'evolution' }]" :aria-pressed="view === 'evolution'" @click="showEvolution"><span>↻</span><span>Evolution<small>GMAT CR · evidence to service</small></span></button>
      <button :class="['workflow-nav', { active: view === 'evidence' }]" :aria-pressed="view === 'evidence'" @click="showEvidence"><span>▤</span><span>Evidence &amp; sources<small>Literature · reliability · provenance</small></span></button>
      <button :class="['workflow-nav', { active: view === 'uploads' }]" :aria-pressed="view === 'uploads'" @click="showUploads"><span>⇄</span><span>Upload learning<small>New evidence · local evaluation</small></span></button>
      <div class="sidebar-bottom"><span class="ledger-icon">≡</span><strong>Evidence before claims</strong><p>Protocols, versioned runs and measured outcomes.</p><a href="https://github.com/Keefit-Inc/questionize/tree/main/research" target="_blank" rel="noreferrer">Open research record ↗</a><a href="/snap">Open learner app ↗</a></div>
    </aside>

    <main class="main">
      <header class="topbar"><span><span class="crumb">Research</span><span class="slash">/</span>{{ view === 'uploads' ? 'Upload learning' : view === 'evolution' ? 'Evolution' : view === 'evidence' ? 'Evidence & sources' : GROUPS.find((item) => item.id === group)?.name }}</span><span class="readonly"><span class="status-dot" /> {{ view === 'evolution' || view === 'uploads' ? 'Live cycle registry' : 'Published aggregates · read only' }}</span></header>
      <EvolutionConsole v-if="view === 'evolution'" @completed="refresh" />
      <EvidenceConsole v-else-if="view === 'evidence'" :registry="data?.evidence" />
      <UploadLearningConsole v-else-if="view === 'uploads'" />
      <div v-else class="content">
        <div class="page-heading"><div><p class="eyebrow">CONTINUOUS CAPABILITY EVALUATION</p><h1>Measure. Compare. Improve.</h1><p class="subtitle">A shared record of what changed, what was tested, and what the evidence supports.</p></div><button class="button" :disabled="loading" @click="refresh">↻ {{ loading ? "Refreshing…" : "Refresh" }}</button></div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <p v-if="!data && loading" class="empty">Loading the experiment ledger…</p>
        <template v-if="data">
          <div class="filters">
            <label>SUBJECT<select v-model="subject" aria-label="Subject"><option v-for="item in data.subjects" :key="item" :value="item">{{ subjectName(item) }} ({{ item }})</option></select></label>
            <label>MEASURE<select v-model="capability" aria-label="Measure"><option v-for="item in capabilities" :key="item.id" :value="item.id">{{ item.id }} · {{ item.name }}</option></select></label>
            <label>EVALUATION SCOPE<select v-model="scope" aria-label="Evaluation scope"><option value="full">Full evaluations</option><option value="trial">Trial runs</option><option value="regression">Replay regressions</option><option value="all">All runs</option></select></label>
            <label>CONDITION<select v-model="condition" aria-label="Result condition"><option value="all">All conditions</option><option v-for="item in conditions" :key="item">{{ item }}</option></select></label>
          </div>
          <div class="stats-grid">
            <div class="stat"><p>Recorded runs <span>↗</span></p><strong>{{ data.runs.filter((run) => run.subject === subject).length }}</strong><small>{{ data.runs.filter((run) => run.subject === subject && run.scope === 'full').length }} full · {{ data.runs.filter((run) => run.subject === subject && run.scope === 'trial').length }} trials · {{ data.runs.filter((run) => run.subject === subject && run.scope === 'regression').length }} regressions</small></div>
            <div class="stat"><p>Measured capabilities <span>◎</span></p><strong>{{ measuredGroups.size }}<span class="denom"> / 6</span></strong><small>{{ metricCount }} measured {{ metricCount === 1 ? 'sub-capability' : 'sub-capabilities' }} · {{ subject }}</small></div>
            <div class="stat"><p>Evidence in this view <span>▤</span></p><strong>{{ records.length }}</strong><small>Condition results · {{ scope === 'all' ? 'all scopes' : scope + ' only' }}</small></div>
            <div class="stat"><p>Last recorded run <span>◷</span></p><strong class="date-stat">{{ timestamp(data.updated_at).split(',')[0] }}</strong><small>{{ timestamp(data.updated_at) }}</small></div>
          </div>

          <section class="panel performance">
            <div class="panel-heading"><div><p class="eyebrow">{{ capability }} · {{ subjectName(subject) }}</p><h2>{{ selectedCapability?.name }} over time</h2></div><span :class="['scope-badge', { trial: scope !== 'full' }]">{{ scope === 'full' ? 'FULL EVALUATIONS' : scope === 'trial' ? 'TRIAL RUNS' : scope === 'regression' ? 'RECORDED REPLAY' : 'MIXED SCOPES' }}</span></div>
            <p class="bar-text">Evaluation bar: {{ selectedCapability?.bar }}</p>
            <details v-if="qualifications.length" class="quality-note">
              <summary><strong>Provisional evidence</strong> · {{ qualifications.length }} data or method qualifications</summary>
              <p>Raw observations are retained. Resolve these qualifications before treating the results as evidence for adopting a change.</p>
              <ul><li v-for="item in qualifications" :key="item.id">{{ item.summary }} <a v-if="item.report_url" :href="item.report_url" target="_blank" rel="noreferrer">Evaluation notes ↗</a></li></ul>
            </details>
            <template v-if="records.length">
              <div class="latest-values"><div v-for="record in currentRecords" :key="record.condition"><span class="condition-label"><i :style="{ background: color(record.condition) }" />{{ record.condition }}</span><strong>{{ percentage(record.value) }}</strong><small>n = {{ record.n ?? 'unrecorded' }}<template v-if="record.ci95"> · 95% CI {{ percentage(record.ci95[0]) }}–{{ percentage(record.ci95[1]) }}</template></small></div></div>
              <div class="chart-wrap"><svg class="chart" viewBox="0 0 790 282" role="img" :aria-label="`${selectedCapability?.name} results and 95 percent confidence intervals by run`">
                <g v-for="tick in [0, .25, .5, .75, 1]" :key="tick"><line x1="60" x2="735" :y1="y(tick)" :y2="y(tick)" stroke="#e7ebef" /><text x="45" :y="y(tick) + 4" text-anchor="end">{{ tick * 100 }}%</text></g>
                <polyline v-for="name in series" :key="name" :points="path(name)" fill="none" :stroke="color(name)" stroke-width="2" stroke-dasharray="4 5" />
                <g v-for="record in records" :key="record.run_id + record.condition" class="chart-point" tabindex="0" role="button" :aria-label="`${record.condition}, ${percentage(record.value)}, n ${record.n}, run ${shortId(record.run_id)}`" @click="selectedRun = record.run_id" @keydown.enter="selectedRun = record.run_id" @keydown.space.prevent="selectedRun = record.run_id">
                  <title>{{ record.condition }} · {{ percentage(record.value) }} · n={{ record.n }} · {{ record.run_id }}</title>
                  <template v-if="record.ci95"><line :x1="x(record)" :x2="x(record)" :y1="y(record.ci95[0])" :y2="y(record.ci95[1])" :stroke="color(record.condition)" opacity=".65" stroke-width="2" /><line :x1="x(record)-5" :x2="x(record)+5" :y1="y(record.ci95[0])" :y2="y(record.ci95[0])" :stroke="color(record.condition)" /><line :x1="x(record)-5" :x2="x(record)+5" :y1="y(record.ci95[1])" :y2="y(record.ci95[1])" :stroke="color(record.condition)" /></template>
                  <circle :cx="x(record)" :cy="y(record.value)" r="6" :fill="color(record.condition)" stroke="white" stroke-width="2" />
                </g>
                <text v-for="id in chartRuns" :key="id" :x="82 + (chartRuns.length > 1 ? chartRuns.indexOf(id) / (chartRuns.length - 1) * 620 : 310)" y="265" text-anchor="middle">{{ shortId(id) }} · {{ runMap.get(id)?.scope }}</text>
              </svg></div>
              <p class="chart-note">Points are observed results; whiskers are recorded 95% intervals. Select a point to inspect its provenance. A higher point alone does not establish an improvement.</p>
            </template>
            <div v-else class="empty"><span class="empty-symbol">◎</span><h3>No measurements yet</h3><p>{{ selectedCapability?.name }} has no {{ scope === 'all' ? '' : scope }} results for {{ subjectName(subject) }}. Other capability scores are not substituted.</p><a :href="`https://github.com/Keefit-Inc/questionize/tree/main/research/capabilities/${({ C1:'C1-capture', C2:'C2-understand', C3:'C3-solve-explain', C4:'C4-diagnose', C5:'C5-write-practice', C6:'C6-choose-practice' } as Record<string,string>)[group]}`" target="_blank" rel="noreferrer">Read the capability definition ↗</a></div>
          </section>

          <div class="two-columns">
            <section class="panel comparison"><div class="panel-heading"><div><p class="eyebrow">PAIRED REVIEW</p><h2>Compare two runs</h2></div><span class="small-label">{{ selectedCapability?.metric.replace(/_/g, ' ') }}</span></div>
              <div class="comparison-selects"><label>BEFORE<select v-model="beforeId" aria-label="Before run"><option v-for="run in runs" :key="run.run_id" :value="run.run_id">{{ shortId(run.run_id) }} · {{ run.memory ? '+ memory' : 'baseline' }} · n={{ run.n_items }}</option></select></label><label>AFTER<select v-model="afterId" aria-label="After run"><option v-for="run in runs" :key="run.run_id" :value="run.run_id">{{ shortId(run.run_id) }} · {{ run.memory ? '+ memory' : 'baseline' }} · n={{ run.n_items }}</option></select></label><label>CONDITION<select v-model="compareCondition" aria-label="Comparison condition"><option v-for="item in comparisonConditions" :key="item">{{ item }}</option></select></label></div>
              <template v-if="left && right && beforeId !== afterId"><div class="compare-values"><div><small>{{ left.condition }}</small><strong>{{ percentage(comparison.leftValue) }}</strong><span>n = {{ comparison.leftN }}</span></div><span class="compare-arrow">→</span><div><small>{{ right.condition }}</small><strong>{{ percentage(comparison.rightValue) }}</strong><span>n = {{ comparison.rightN }}</span></div><div class="delta"><small>{{ comparison.matchedSubset ? 'MATCHED CHANGE' : 'OBSERVED CHANGE' }}</small><strong v-if="difference != null">{{ difference > 0 ? '+' : '' }}{{ difference.toFixed(2) }}<span> pp</span></strong><strong v-else>—</strong></div></div>
                <p v-if="comparison.matchedSubset" class="paired-result matched-subset">Matched subset of baseline run ({{ comparison.leftN }} of {{ comparison.baselineTotal }}). Both scores and the paired interval use these same {{ comparison.leftN }} items.</p>
                <p v-else-if="difference == null" class="paired-result">Different or unrecorded sample sizes: an aggregate change is not shown.<template v-if="paired?.diff_ci95"> The recorded paired interval concerns overlapping items, not the two aggregate scores above.</template></p>
                <p v-if="paired?.diff_ci95" class="paired-result">Recorded paired 95% CI: {{ (paired.diff_ci95[0] * 100).toFixed(2) }} to {{ (paired.diff_ci95[1] * 100).toFixed(2) }} pp<template v-if="paired.p != null"> · McNemar p = {{ paired.p }}</template></p>
                <div :class="['comparison-note', { caution: issues.length }]"><strong>{{ issues.length ? 'Review comparison conditions' : 'Recorded settings match' }}</strong><ul v-if="issues.length"><li v-for="issue in issues" :key="issue">{{ issue }}</li></ul><p v-else>Settings match on the recorded fields. Inspect sample size, paired outcomes and uncertainty before accepting a change.</p></div>
              </template><p v-else class="empty compact">Select two runs with results for the same measure and condition.</p>
            </section>
            <section class="panel provenance"><div class="panel-heading"><div><p class="eyebrow">REPRODUCIBILITY</p><h2>Run provenance</h2></div><span v-if="detail" class="scope-badge">{{ detail.scope }}</span></div>
              <template v-if="detail"><strong class="run-id">{{ detail.run_id }}</strong><p class="run-note">{{ detail.note || 'No change note recorded.' }}</p><dl><dt>Protocol</dt><dd>{{ detail.protocol }} v{{ detail.protocol_version }} · {{ detail.split }} split</dd><dt>Dataset</dt><dd>{{ detail.dataset_id }}<code>{{ detail.dataset_hash }}</code></dd><dt>Models</dt><dd v-for="(model, role) in detail.models" :key="role">{{ role }}: {{ model }}</dd><dt>Memory</dt><dd>{{ detail.memory ? `${detail.memory.lessons} rules` : 'Off' }}<code v-if="detail.memory">{{ detail.memory.hash }}</code></dd><dt>Prompts / code</dt><dd><code>{{ detail.prompts_hash }}</code></dd><dt>Source commit</dt><dd><a :href="`https://github.com/Keefit-Inc/questionize/commit/${detail.git_sha}`" target="_blank" rel="noreferrer">{{ detail.git_sha?.slice(0, 10) }} ↗</a></dd><dt>Recorded</dt><dd>{{ timestamp(detail.started_at) }}</dd></dl></template><p v-else class="empty compact">Select a run to inspect its recorded configuration.</p>
            </section>
          </div>
          <section class="panel history"><div class="panel-heading"><div><p class="eyebrow">APPEND-ONLY EXPERIMENT LEDGER</p><h2>Condition history <span class="count">{{ records.length }}</span></h2></div><button class="button small" :disabled="!records.length" @click="download">↓ Export view</button></div>
            <div class="table-scroll"><table><thead><tr><th>Run / change</th><th>Condition</th><th>Result</th><th>95% interval</th><th>Sample</th><th>Calls</th><th>ECE</th><th>Scope</th></tr></thead><tbody><tr v-for="record in sortedRecords" :key="record.run_id + record.condition" :class="{ selected: selectedRun === record.run_id }"><td><button class="run-link" @click="selectedRun = record.run_id">{{ shortId(record.run_id) }} ↗</button><small>{{ runMap.get(record.run_id)?.note }}</small></td><td><span class="condition-label"><i :style="{ background: color(record.condition) }" />{{ record.condition }}</span></td><td class="numeric strong">{{ percentage(record.value) }}</td><td class="numeric">{{ record.ci95 ? `${percentage(record.ci95[0])}–${percentage(record.ci95[1])}` : 'Not recorded' }}</td><td class="numeric">{{ record.n ?? '—' }}<span v-if="record.complete === false" class="missing"> / {{ record.expected_n }} incomplete</span></td><td class="numeric">{{ record.calls ?? '—' }}</td><td class="numeric">{{ record.ece?.toFixed(4) ?? '—' }}</td><td><span :class="['scope-badge', { trial: record.scope === 'trial' }]">{{ record.scope }}</span></td></tr><tr v-if="!records.length"><td colspan="8" class="empty">No condition results in this view.</td></tr></tbody></table></div>
          </section>
          <footer><span>● Published aggregate record. Item text, model outputs and human rating sheets remain private.</span><span>Ledger snapshot · {{ timestamp(data.updated_at) }}</span></footer>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.workflow-nav { width:100%; display:flex; align-items:center; gap:14px; border:1px solid #304552; background:#192c37; color:#a5c0c9; padding:13px; margin-top:20px; border-radius:7px; text-align:left; font-weight:600; font-size:12px; }
.workflow-nav>span:first-child { font-size:22px; color:#7fbfa8; }
.workflow-nav small { display:block; font-weight:400; font-size:10px; color:#738e9c; margin-top:5px; }
.workflow-nav.active { background:#294739; border-color:#456956; color:#e0eee5; }
@media(max-width:760px) { .workflow-nav { margin-top:10px; padding:9px 12px; justify-content:center; font-size:11px; }.workflow-nav small { display:inline; margin-left:8px; font-size:9px; }.workflow-nav>span:first-child { font-size:17px; } }
</style>
