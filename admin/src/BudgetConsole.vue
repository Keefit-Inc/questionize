<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { percentage, timestamp, type BudgetStudy } from "./research";
const props = defineProps<{ studies?: BudgetStudy[] }>();
const study = computed(() => props.studies?.at(-1));
const production = ref<{ version?: number; runtime?: string } | null>(null);
const labels: Record<string,string> = { A: "Meta baseline", M: "Training-derived memory", MV: "Memory + verifier" };
const money = (value: number | undefined) => value == null ? "not recorded" : `$${value.toFixed(4)}`;
const interval = (values?: [number, number]) => values ? `${percentage(values[0])}–${percentage(values[1])}` : "not recorded";
const repo = (path: string) => `https://github.com/Keefit-Inc/questionize/blob/main/${path}`;
const total = computed(() => study.value ? Object.values(study.value.conditions).reduce((sum, c) => sum + c.estimated_billed_usd, 0)
  + study.value.training_estimated_billed_usd + (study.value.development_estimated_billed_usd ?? 0) : 0);
onMounted(async () => {
  try {
    const response = await fetch("/admin/uploads", { cache: "no-store" });
    if (response.ok) { const value = await response.json(); production.value = { version: value.active_memory?.version, runtime: value.runtime }; }
  } catch { /* A published experiment remains readable when live status is unavailable. */ }
});
</script>

<template>
  <div class="content budget-console">
    <div class="page-heading"><div><p class="eyebrow">E14 · GMAT CR</p><h1>Memory under the same budget</h1><p class="subtitle">Frozen source splits, metered Meta calls, and separate Solver / verifier failure evidence.</p></div></div>
    <p v-if="!study" class="empty">No completed budget comparison has been published. An unfinished run is not a result.</p>
    <template v-else>
      <section class="panel">
        <p class="eyebrow">{{ study.run_id }} · {{ timestamp(study.started_at) }}</p>
        <h2>{{ study.decision === 'held' ? 'Held — improvement not established' : 'Observed gain — independent confirmation required' }}</h2>
        <p>{{ study.model }} · reasoning effort {{ study.reasoning_effort }} · {{ money(study.envelope_usd) }} per item per condition.</p>
        <p class="quality-note">The uncached token-price ceiling is equal; actual expenditure can differ. Hidden reasoning is included in output tokens. Cache discounts do not expand the budget. Source-key agreement is not human-certified correctness.</p>
        <p v-if="!study.cost_comparison_valid" class="error" role="alert">Cost accounting is incomplete or a budget was exceeded. Do not interpret this run as a valid cost-matched comparison.</p>
        <div class="links"><a :href="repo(study.protocol_path)" target="_blank" rel="noreferrer">Registered protocol ↗</a><a :href="repo(study.report_path)" target="_blank" rel="noreferrer">Results and limitations ↗</a></div>
      </section>
      <section class="panel">
        <h2>Training and evaluation stayed separate</h2>
        <div class="split-grid"><article v-for="name in ['train', 'development', 'test', 'held']" :key="name"><strong>{{ study.split.counts[name] }}</strong><span>{{ name }} · {{ study.split.groups[name] }} stimulus groups</span><code>{{ study.split.membership_hashes[name] }}</code></article></div>
        <p>Cross-partition stimulus overlap after screening: {{ study.split.cross_partition_group_overlap }}. Keys and reference explanations are hidden from every final Solver and verifier call. The key-only compilation is excluded.</p>
        <p>Learned procedures: {{ study.procedure_count }} · construction calls: {{ study.training_calls }} · construction failures: {{ study.training_failures }} · a procedure was retrieved for {{ study.memory_retrieval_covered ?? 'unrecorded' }}/{{ study.split.counts.test }} test items. The procedures are AI-derived from private expert references; their contents remain private.</p>
        <p class="chart-note">Exact and five-gram similarity checks cannot establish semantic independence or absence from model pretraining. No learner traffic is represented by this batch.</p>
      </section>
      <section class="panel">
        <h2>Accuracy, expenditure and completion</h2>
        <div class="table-wrap"><table><thead><tr><th>Condition</th><th>Correct / registered</th><th>95% interval</th><th>Normalised spend</th><th>Estimated billed</th><th>Mean latency</th><th>Errors</th></tr></thead><tbody>
          <tr v-for="(condition, arm) in study.conditions" :key="arm"><td>{{ arm }} · {{ labels[arm] }}</td><td>{{ condition.correct }}/{{ condition.n }} · {{ percentage(condition.accuracy) }}</td><td>{{ interval(condition.ci95) }}</td><td>{{ money(condition.normalised_usd) }}</td><td>{{ money(condition.estimated_billed_usd) }}</td><td>{{ condition.mean_seconds.toFixed(1) }}s</td><td>{{ condition.errors }}</td></tr>
        </tbody></table></div>
        <p>Construction: {{ money(study.training_estimated_billed_usd) }} · development smoke: {{ money(study.development_estimated_billed_usd) }} · complete experiment estimate: {{ money(total) }}. These are response-usage token-price estimates, not account invoices.</p>
        <details><summary>Paired evidence and token accounting</summary>
          <article v-for="(condition, arm) in study.conditions" :key="arm"><h3>{{ labels[arm] }}</h3><p>{{ condition.calls }} generation calls · {{ condition.input_tokens }} input · {{ condition.output_tokens }} output ({{ condition.reasoning_tokens }} reasoning, already included) · {{ condition.cached_tokens }} cached input. Usage complete: {{ condition.usage_complete ? 'yes' : 'no' }}. Budget violations: {{ condition.budget_violations }}.</p><p v-if="arm !== 'A'">Against A: gained {{ condition.vs_baseline?.b }}, lost {{ condition.vs_baseline?.c }}. Difference interval {{ interval(condition.vs_baseline?.diff_ci95) }}; McNemar p={{ condition.vs_baseline?.p }}. The paired interval uses stimulus-group resampling.</p></article>
          <p><a :href="study.price_url" target="_blank" rel="noreferrer">Meta prices ↗</a> · reviewed {{ study.price_reviewed }} · per million tokens: input {{ money(study.rates.input) }}, cached input {{ money(study.rates.cached_input) }}, output {{ money(study.rates.output) }}.</p>
        </details>
      </section>
      <section class="panel">
        <h2>Where did verification help or fail?</h2>
        <div class="split-grid"><article><strong>{{ study.diagnostics.rescue }}</strong><span>wrong → right · rescued</span></article><article><strong>{{ study.diagnostics.harm }}</strong><span>right → wrong · harmed</span></article><article><strong>{{ study.diagnostics.both_wrong }}</strong><span>both proposed answers wrong</span></article><article><strong>{{ study.diagnostics.operational_error }}</strong><span>operational failures</span></article></div>
        <p>These transitions compare MV's first Solver with its verifier, not A with MV. The verifier uses the same model and sees the proposed answer; it is not an independent ground-truth authority.</p>
        <p v-if="study.diagnostics.harm > 0">Selection weakness is directly observed: the first answer was correct in {{ study.diagnostics.harm }} cases and the verifier replaced it with a wrong answer.</p>
        <p v-if="study.diagnostics.both_wrong > 0">In {{ study.diagnostics.both_wrong }} cases neither answer matched the source. This exposes unresolved reasoning under this procedure and budget; it does not prove a fundamental model ceiling or establish that fine-tuning is required.</p>
        <p v-if="study.diagnostics.operational_error > 0">Inspect the report's truncation, schema and budget errors before attributing all failures to reasoning.</p>
        <div class="table-wrap"><table><thead><tr><th>Stem-routed type</th><th>n</th><th>A correct</th><th>M correct</th><th>MV correct</th></tr></thead><tbody><tr v-for="(slice, type) in study.slices" :key="type"><td>{{ type }}</td><td>{{ slice.n }}</td><td>{{ slice.A }}</td><td>{{ slice.M }}</td><td>{{ slice.MV }}</td></tr></tbody></table></div>
      </section>
      <section class="panel">
        <h2>Research candidate and running service</h2>
        <p>Research candidate deployed: <strong>No</strong>. {{ production?.version != null ? `Live service memory: v${production.version} · ${production.runtime}.` : 'Live service version is not currently observed.' }} <a href="/admin#uploads">Inspect the active release ↗</a></p>
        <p class="quality-note">A positive sample result requires a new confirmation set before a release decision. No gain remains held. This study does not measure human explanation quality, generated-item validity, or learner growth.</p>
        <details><summary>Frozen artifact hashes</summary><p>Memory <code>{{ study.memory_hash }}</code></p><p>Manifest <code>{{ study.manifest_hash }}</code></p><p>Runner <code>{{ study.runner_hash }}</code></p><p>Metered client <code>{{ study.client_hash }}</code></p></details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.panel{margin-bottom:24px}.split-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:20px 0}.split-grid article{display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid #dce5e9;border-radius:8px;min-width:0}.split-grid strong{font-size:28px}.split-grid span{font-size:13px;color:#526575}code{overflow-wrap:anywhere;font-size:11px}.quality-note{padding:12px;border-left:3px solid #d9a854;background:#fff9ed}.links{display:flex;gap:20px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left}td,th{padding:12px 8px;border-bottom:1px solid #e2e8ed;white-space:nowrap}summary{cursor:pointer;font-weight:650}@media(max-width:900px){.split-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:500px){.split-grid{grid-template-columns:1fr}}
</style>
