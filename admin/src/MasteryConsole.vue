<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { percentage, timestamp, type MasteryStudy } from "./research";
const props=defineProps<{studies?:MasteryStudy[]}>();
const study=computed(()=>props.studies?.at(-1));
const live=ref<number|null>(null);
const names:Record<string,string>={SM:'Spark · medium',S:'Spark · high',P:'Spark · mechanisms',W:'Wonder · high',PW:'Wonder · mechanisms'};
const roles:Record<string,string>={official_regression:'Official OG · exposed',web_regression:'Publisher / instructor · exposed',compendium_development:'Key-only development',confirmation:'Frozen key-only confirmation',held:'Held before inference'};
const stages:Record<string,string>={pilot:'Known failure probes and controls',effort:'Effort control · official development',ogdev:'Official development · four methods',docdev:'Key-only development · candidate selection',confirm:'Frozen confirmation',regression:'Broad exposed regression'};
const candidate=computed(()=>study.value?.candidate ?? '');
const official=computed(()=>study.value?.phases.regression?.roles.official_regression?.[candidate.value]);
const confirmation=computed(()=>study.value?.phases.confirm?.conditions[candidate.value]);
const money=(value:number|undefined)=>value==null?'—':`$${value.toFixed(4)}`;
const repo=(path:string)=>`https://github.com/Keefit-Inc/questionize/blob/main/${path}`;
onMounted(async()=>{try{const response=await fetch('/admin/uploads',{cache:'no-store'});if(response.ok)live.value=(await response.json()).active_memory?.version ?? null;}catch{/* Historical results remain readable. */}});
</script>

<template>
  <div class="content mastery-console">
    <div class="page-heading"><div><p class="eyebrow">E15 · GMAT CR SOLVING FIRST</p><h1>Toward complete solving</h1><p class="subtitle">Known failure closure, broad private sources, and fresh confirmation kept separate.</p></div></div>
    <p v-if="!study" class="empty">No completed mastery study has been published. A target of 100% is not an achieved result.</p>
    <template v-else>
      <section class="panel">
        <p class="eyebrow">{{ study.run_id }} · {{ timestamp(study.started_at) }}</p>
        <div class="score-grid"><article><strong>{{ official?.correct ?? '—' }}/{{ official?.n ?? '—' }}</strong><span>Official OG regression · previously exposed</span></article><article><strong>{{ confirmation?.correct ?? '—' }}/{{ confirmation?.n ?? '—' }}</strong><span>Frozen confirmation · supplied keys</span></article><article><strong>{{ study.unique_evaluated }}</strong><span>Unique questions evaluated · repeat trials counted once</span></article></div>
        <p>Selected configuration: <strong>{{ names[study.candidate] }}</strong>. {{ study.interpretation === 'model_upgrade' ? 'This is a model upgrade; its gains are not attributed to learned memory.' : study.interpretation === 'procedure_tool_comparison' ? 'The procedure/tool comparison uses a direct baseline of the same model.' : 'The baseline was retained after development.' }}</p>
        <p><strong>{{ study.official_closed ? 'All 124 official regression answers matched their source keys in this pass.' : 'Official regression closure remains incomplete.' }}</strong> {{ study.decision === 'confirmation_candidate' ? 'Fresh paired evidence supports a release candidate; deployment is a separate step.' : 'The registered release criteria were not all met; research candidate held.' }}</p>
        <p class="quality-note">Known regressions are development evidence. A perfect finite cohort does not certify every future question. The compendium has supplied answer keys, no expert explanations and no independent human adjudication; report its agreement separately from official OG.</p>
        <div class="links"><a :href="repo(study.protocol_path)" target="_blank" rel="noreferrer">Protocol ↗</a><a :href="repo(study.clarification_path)" target="_blank" rel="noreferrer">Pre-confirmation clarification ↗</a><a :href="repo(study.report_path)" target="_blank" rel="noreferrer">Results and limitations ↗</a></div>
      </section>
      <section class="panel"><h2>Source confidence and frozen membership</h2>
        <div class="table-wrap"><table><thead><tr><th>Role</th><th>Questions</th><th>Stimulus groups</th></tr></thead><tbody><tr v-for="(n,role) in study.split.counts" :key="role"><td>{{ roles[role] }}</td><td>{{ n }}</td><td>{{ study.split.groups[role] }}</td></tr></tbody></table></div>
        <p>Confirmation overlap with exposed/development stimuli: {{ study.split.confirmation_overlap }}. LSAT items are not used. Source originals, keys, expert text, private procedures and per-item outputs remain local; only question fields enter blind Standard Meta inference.</p>
        <details><summary>Membership hashes</summary><p v-for="(hash,role) in study.split.hashes" :key="role">{{ role }} <code>{{ hash }}</code></p></details>
        <div v-if="study.preparation?.restored_questions" class="quality-note"><p>Source correction: {{ study.preparation.restored_questions }} shared-stimulus records restored from the original source; {{ study.preparation.keys_changed }} key changes, {{ study.preparation.choices_changed }} choice changes. The earlier {{ study.preparation.invalid_evaluated_questions }}-observation compilation phase is excluded as invalid input evidence, not selectively rescored. Its known cost and interrupted-request upper bound remain in the study budget.</p><p>Request reconstruction: {{ study.blinding_passed ? 'passed' : 'not confirmed' }} · {{ study.matched_requests }}/{{ study.audited_requests }}. Unchanged official controls were reused with a request-hash certificate.</p></div>
      </section>
      <section class="panel"><h2>Final confirmation</h2>
        <p>{{ study.phases.confirm?.evaluated }}/{{ study.phases.confirm?.registered }} registered questions evaluated. {{ study.phases.confirm?.budget_limited ? 'Budget-limited; the unattempted remainder is not counted as solved.' : 'All registered confirmation items were attempted.' }}</p>
        <div class="table-wrap"><table><thead><tr><th>Condition</th><th>Source matches</th><th>95% interval</th><th>Normalised cost</th><th>Estimated billed</th><th>Errors</th></tr></thead><tbody><tr v-for="(c,arm) in study.phases.confirm?.conditions" :key="arm"><td>{{ names[arm] }}</td><td>{{ c.correct }}/{{ c.n }} · {{ percentage(c.accuracy) }}</td><td>{{ c.ci95 ? `${percentage(c.ci95[0])}–${percentage(c.ci95[1])}` : '—' }}</td><td>{{ money(c.normalised_usd) }}</td><td>{{ money(c.estimated_billed_usd) }}</td><td>{{ c.errors }}</td></tr></tbody></table></div>
        <p v-for="(c,arm) in study.phases.confirm?.conditions" :key="arm"><template v-if="c.comparison">{{ names[arm] }} versus {{ names[c.baseline ?? 'S'] }}: gained {{ c.comparison.b }}, lost {{ c.comparison.c }} · paired change {{ ((c.comparison.difference ?? 0)*100).toFixed(2) }} pp · McNemar p={{ c.comparison.p }}.</template></p>
        <p class="chart-note">The final candidate and every comparison configuration were frozen before confirmation. Same per-item ceilings do not mean identical realised spending. Model effects and procedure effects are distinct.</p>
      </section>
      <section class="panel"><h2>Development and regression evidence</h2>
        <details v-for="(phase,name) in study.phases" :key="name" :open="name === 'regression'"><summary>{{ stages[name] }} · {{ phase.evaluated }}/{{ phase.registered }} observations · {{ phase.unique_questions }} unique questions</summary>
          <div class="table-wrap"><table><thead><tr><th>Condition</th><th>Source matches</th><th>Errors</th><th>Known hard trials</th><th>Cost estimate</th><th>Tool rescue / harm</th></tr></thead><tbody><tr v-for="(c,arm) in phase.conditions" :key="arm"><td>{{ names[arm] }}</td><td>{{ c.correct }}/{{ c.n }}</td><td>{{ c.errors }} · repair failures {{ c.repair_errors }}</td><td>{{ c.hard_correct }}/{{ c.hard_trials }} · {{ c.hard_closed }}/{{ c.hard_unique }} cases closed</td><td>{{ money(c.estimated_billed_usd) }}</td><td>{{ c.repair_rescues }} / {{ c.repair_harms }}</td></tr></tbody></table></div>
          <p v-if="name === 'pilot'" class="chart-note">Two hard cases were deliberately repeated. Ten responses represent eight unique questions, not ten independent tests.</p>
          <p v-if="phase.budget_limited" class="quality-note">This phase stopped at the global resource limit. See the evaluated membership and unattempted count.</p>
          <p v-for="(values,role) in phase.roles" :key="role"><span v-for="(c,arm) in values" :key="arm">{{ roles[role] }} · {{ names[arm] }} {{ c.correct }}/{{ c.n }}. </span></p>
        </details>
      </section>
      <section class="panel"><h2>Resources, provenance and service</h2>
        <p>Normalised generation cost {{ money(study.normalised_usd) }} · estimated billed {{ money(study.estimated_billed_usd) }} · conservative charge {{ money(study.charged_usd) }} / {{ money(study.budget_limit_usd) }} study envelope. Hidden reasoning and failed output are included. Complete usage: {{ study.cost_accounting_complete ? 'yes' : 'no' }}.</p>
        <p>Research candidate deployed: <strong>No</strong>. Live solving-memory version: {{ live == null ? 'not observed' : `v${live}` }}. Model configuration and learned-memory versions are separate; this experiment does not train model weights.</p>
        <p class="quality-note">Input structure, answer uniqueness, human explanation quality, generated-item validity and learner growth are separate capabilities. Source agreement or model consensus does not certify them.</p>
        <details><summary>Frozen configuration hashes</summary><p>Manifest <code>{{ study.manifest_hash }}</code></p><p>Private mechanism policy <code>{{ study.policy_hash }}</code></p><p>Source <code>{{ study.source_hash }}</code></p></details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.panel{padding:24px;margin-bottom:24px}.score-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0}.score-grid article{padding:18px;border:1px solid #dce5e9;border-radius:8px;display:flex;flex-direction:column;gap:8px}.score-grid strong{font-size:30px}.score-grid span,.chart-note{font-size:13px;color:#526575}.links{display:flex;flex-wrap:wrap;gap:16px}.quality-note{padding:12px;border-left:3px solid #d9a854;background:#fff9ed}.table-wrap{overflow-x:auto}table{border-collapse:collapse;text-align:left;width:100%}td,th{padding:12px 8px;border-bottom:1px solid #e2e8ed;white-space:nowrap}details{padding:12px 0}summary{cursor:pointer;font-weight:650}code{font-size:11px;overflow-wrap:anywhere}@media(max-width:800px){.score-grid{grid-template-columns:1fr}}
</style>
