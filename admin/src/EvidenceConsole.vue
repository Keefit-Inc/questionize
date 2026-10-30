<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { GROUPS, percentage, type EvidenceRegistry } from "./research";
const props = defineProps<{ registry?: EvidenceRegistry }>();
const capability = ref("all");
const live = ref<{ origins: Record<string, number>; statuses: Record<string, number> } | null>(null);
const liveError = ref("");
const service = ref<{ status: string; observed_at?: string; integrity_guard?: { version: string; enabled: boolean } } | null>(null);
const activePolicy = ref<number | null>(null);
const papers = computed(() => props.registry?.papers.filter(p => capability.value === "all" || p.capabilities.some(c => c.split(".")[0] === capability.value)) ?? []);
const repo = (path: string) => `https://github.com/Keefit-Inc/questionize/blob/main/${path}`;
async function refreshSources() {
  try {
    const response = await fetch("/admin/cycles", { cache: "no-store" });
    if (!response.ok) throw new Error("Live source counts unavailable");
    const payload = await response.json();
    live.value = payload.knowledge_evidence ?? null;
    service.value = payload.verification_service ?? null;
    activePolicy.value = payload.active_policy?.version ?? null;
  } catch { liveError.value = "Live source counts unavailable. Published research evidence is still shown."; }
}
onMounted(refreshSources);
</script>

<template>
  <div class="content evidence-console">
    <div class="page-heading"><div><p class="eyebrow">RESEARCH TO SERVICE</p><h1>Evidence &amp; sources</h1><p class="subtitle">Source fidelity, independent checks and literature connected to actual runs.</p></div></div>
    <p v-if="!registry" class="empty">No evidence registry has been published.</p>
    <template v-else>
      <section class="panel"><p class="eyebrow">GMAT CR · PILOT BOUNDARY</p><h2>What is ready to test</h2><p>Input-format guards, evidence confidence, independent blind solving, private local research and measured release gates are implemented. A verified reference remains valuable: matching AI answers can still be wrong.</p><p class="quality-note">C1 character fidelity, C2 expert tag agreement, C3 human explanation quality, C4 learner diagnosis and C6 learning benefit remain unmeasured. C5 first-draft verification below is an AI proxy. Start with a small operator pilot; these results do not certify 99.9% accuracy.</p></section>
      <section class="panel">
        <div class="panel-heading"><div><p class="eyebrow">SEPARATE KNOWLEDGE ORIGINS</p><h2>Expert references ≠ usage-derived knowledge</h2></div></div>
        <div class="evidence-origins"><article><h3>Expert-reference namespace</h3><p>{{ registry.knowledge_policy.expert_reference }}</p><strong>Private source material · attributed derivatives</strong></article><article><h3>User-experience namespace</h3><p>{{ registry.knowledge_policy.user_experience }}</p><strong>AI-estimated observations · separate confirmation</strong></article></div>
        <p class="quality-note">{{ registry.knowledge_policy.promotion }} {{ registry.knowledge_policy.rights }}</p>
        <div class="evidence-assets"><article v-for="asset in registry.knowledge_assets" :key="asset.id"><h3>{{ asset.namespace }}</h3><strong>{{ asset.count }} {{ asset.unit }}</strong><p>{{ asset.derivation }}</p><p>{{ asset.evidence_status }} · {{ asset.rights_scope }}</p><p class="chart-note">{{ asset.limitation }}</p><code v-if="asset.artifact_hash" class="evidence-hash">{{ asset.artifact_hash }}</code></article></div>
        <div v-if="live" class="source-counts"><span v-for="(n, origin) in live.origins" :key="origin">{{ origin }}: <strong>{{ n }}</strong></span><span v-for="(n, status) in live.statuses" :key="status">{{ status }}: <strong>{{ n }}</strong></span></div>
        <p v-if="liveError" role="status">{{ liveError }}</p>
        <p v-if="service?.status === 'observed'" class="quality-note">Observed AI service: {{ service.integrity_guard?.version ?? 'guard version unavailable' }} · enabled {{ service.integrity_guard?.enabled === true ? 'yes' : 'not confirmed' }} · {{ service.observed_at }}. Active GMAT CR policy: v{{ activePolicy ?? '?' }}. <a href="/admin#evolution">Inspect policy and adoption evidence ↗</a></p>
        <p v-else class="chart-note">Running AI guard status: {{ service?.status ?? 'not observed' }}. Published experiment results do not by themselves prove a deployment.</p>
      </section>
      <section v-for="audit in registry.capture_audits" :key="audit.id" class="panel">
        <div class="panel-heading"><div><p class="eyebrow">C1 · SOURCE AUDIT</p><h2>{{ audit.id }}</h2></div><a :href="repo(audit.report_path)" target="_blank" rel="noreferrer">Audit report ↗</a></div>
        <div class="audit-stats"><span><strong>{{ audit.total }}</strong> inspected structurally</span><span><strong>{{ audit.restored_emphasis_items }}</strong> emphasis repairs</span><span><strong>{{ audit.restored_identifiers }}</strong> identifier repairs</span><span><strong>{{ audit.held_flagged }}</strong> held captures</span></div>
        <p>{{ audit.membership }}</p><p>{{ audit.visual_review_scope }}. Independent human review: {{ audit.independent_human_review ? 'yes' : 'not yet' }}.</p><code class="evidence-hash">Dataset SHA-256: {{ audit.dataset_hash }}</code>
        <p v-if="audit.ocr_pages">{{ audit.ocr_engines }} · {{ audit.ocr_pages }} OCR pages · {{ audit.printed_keys_crosschecked }} reference keys checked · {{ audit.stimulus_omissions_repaired }} stimulus omissions repaired. {{ audit.unmatched_regions_for_review }} regions could not be automatically aligned and remain separately reviewable.</p>
        <p class="chart-note">Mechanical checks and targeted visual repair do not establish full OCR fidelity or 99.9% solving reliability.</p>
      </section>
      <section v-for="evaluation in registry.evaluations" :key="evaluation.run_id" class="panel">
        <div class="panel-heading"><div><p class="eyebrow">{{ evaluation.protocol }} · {{ evaluation.scope }}</p><h2>{{ ({ E9: 'Solver and Judge separation', E10: 'Defect rejection contracts', E12: 'Completion format and upload readiness', E13: 'Real photos: evidence handling', E2: 'Original practice: matched first drafts' } as Record<string, string>)[evaluation.protocol] ?? 'Capability evaluation' }}</h2></div><a :href="repo(evaluation.report_path)" target="_blank" rel="noreferrer">Results &amp; methods ↗</a></div>
        <p><code>{{ evaluation.run_id }}</code> · {{ evaluation.summary.completed }}/{{ evaluation.summary.expected }} completed · {{ evaluation.summary.errors }} errors</p>
        <div v-if="evaluation.protocol === 'E9'" class="audit-stats"><span v-for="role in ['solver', 'judge', 'legacy', 'guarded']" :key="role"><strong>{{ percentage(evaluation.summary[role]?.accuracy) }}</strong>{{ role }} · {{ evaluation.summary[role]?.correct }}/{{ evaluation.summary[role]?.n }}</span></div>
        <div v-if="evaluation.protocol === 'E10'" class="table-wrap"><table><thead><tr><th>Case type</th><th>Cases</th><th>Legacy accepted</th><th>Guarded accepted</th><th>Integrity blocks</th></tr></thead><tbody><tr v-for="(row, kind) in evaluation.summary.by_type" :key="kind"><td>{{ kind }}</td><td>{{ row.n }}</td><td>{{ row.legacy_accepted }}</td><td>{{ row.guarded_accepted }}</td><td>{{ row.deterministically_blocked }}</td></tr></tbody></table></div>
        <p v-if="evaluation.protocol === 'E9'">Legacy changed a correct Solver answer to wrong: {{ evaluation.summary.legacy?.corrupted }}. Guarded policy: {{ evaluation.summary.guarded?.corrupted }}. Judge applies to {{ evaluation.summary.judge?.n }} items; its subset score is not a full-test score.</p>
        <template v-if="evaluation.protocol === 'E12'">
          <div class="audit-stats"><span v-for="role in ['completion_first', 'completion_repeat', 'previous_test']" :key="role"><strong>{{ evaluation.summary[role]?.correct }}/{{ evaluation.summary[role]?.n }}</strong>{{ role.replaceAll('_', ' ') }}</span></div>
          <p>Repeat answer disagreements: {{ evaluation.summary.repeat_disagreements }}. These are 15 completion items observed twice, plus 39 previous test items; 69 responses are not 69 independent questions.</p>
          <p>Normal input accepted: {{ evaluation.summary.format_contract?.normal_accepted }}/{{ evaluation.summary.format_contract?.normal_n }} · missing-blank defects blocked: {{ evaluation.summary.format_contract?.missing_blank_blocked }}/{{ evaluation.summary.format_contract?.defect_n }}.</p>
        </template>
        <template v-if="evaluation.protocol === 'E2'">
          <div class="audit-stats"><span v-for="condition in ['baseline', 'candidate']" :key="condition"><strong>{{ evaluation.summary[condition]?.passed }}/{{ evaluation.summary[condition]?.first_draft_pass_rate_n }}</strong>{{ condition }} · first-draft verification</span></div>
          <p>Candidate gained {{ evaluation.summary.gained }} paired tasks; lost {{ evaluation.summary.lost }}. Decision: {{ evaluation.summary.adopt ? 'eligible under the registered gate' : 'held; current writer retained' }}. Human pairwise ratings and learner outcomes remain unmeasured.</p>
        </template>
        <template v-if="evaluation.protocol === 'E13'"><p>Evidence-handling contracts: {{ evaluation.summary.evidence_contract_passed }}/{{ evaluation.summary.expected }} · captured text-role matches: {{ evaluation.summary.source_text_roles_equal }}/{{ evaluation.summary.expected }} · main answer matched source: {{ evaluation.summary.correct }}/{{ evaluation.summary.expected }}.</p><p>Three deliberately selected photo scenarios share two hard source questions. Correct evidence handling and correct answers are separate outcomes.</p></template>
        <p><strong>{{ evaluation.decision }}</strong></p><p class="quality-note">{{ evaluation.limitations }}</p>
      </section>
      <section class="panel">
        <div class="panel-heading"><div><p class="eyebrow">LITERATURE → IMPLEMENTATION → EXPERIMENT → RESULT</p><h2>Capability research map</h2></div><label>CAPABILITY<select v-model="capability" aria-label="Literature capability"><option value="all">All capabilities</option><option v-for="g in GROUPS" :key="g.id" :value="g.id">{{ g.id }} · {{ g.name }}</option></select></label></div>
        <p>Reviewed {{ registry.reviewed_at }}. {{ registry.review_scope }}</p>
        <article v-for="paper in papers" :key="paper.id" class="paper-evidence">
          <p class="eyebrow">{{ paper.capabilities.join(' · ') }} <span class="scope-badge">{{ paper.implementation_status.replaceAll('_', ' ') }}</span></p>
          <h3><a :href="paper.url" target="_blank" rel="noreferrer">{{ paper.title }} ↗</a></h3><p>{{ paper.claim }}</p>
          <p><strong>Application limit:</strong> {{ paper.limitations }}</p>
          <div class="evidence-links"><a v-for="path in paper.implementation_paths" :key="path" :href="repo(path)" target="_blank" rel="noreferrer">{{ path }} ↗</a></div>
          <p v-if="!paper.runs.length" class="chart-note">No recorded results for this method. Related protocols: {{ paper.protocols.join(', ') }}. This reference is not evidence of a measured improvement.</p>
          <div v-else class="evidence-links"><a v-for="run in paper.runs" :key="run.run_id" :href="repo(run.report_path)" target="_blank" rel="noreferrer">{{ run.protocol }} · {{ run.scope }} · {{ run.run_id }} ↗</a></div>
        </article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.evidence-assets{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0}.evidence-assets article{padding:16px;border:1px solid #e2e8ed;border-radius:8px;min-width:0}.evidence-assets h3{font-size:13px;overflow-wrap:anywhere}.evidence-assets code{font-size:10px}@media(max-width:1000px){.evidence-assets{grid-template-columns:1fr}}
</style>

<style scoped>
.evidence-console>.panel{margin-bottom:24px}.evidence-origins{display:grid;grid-template-columns:1fr 1fr;gap:24px}.evidence-origins article{padding:18px;border:1px solid #dce5e9;border-radius:8px}.evidence-origins h3,.paper-evidence h3{margin:0 0 10px}.audit-stats{display:flex;flex-wrap:wrap;gap:28px;margin:22px 0}.audit-stats span{display:flex;flex-direction:column;gap:4px;color:#526575}.audit-stats strong{font-size:26px;color:#182b3b}.evidence-hash{display:block;overflow-wrap:anywhere}.source-counts,.evidence-links{display:flex;flex-wrap:wrap;gap:10px 20px;margin:14px 0}.paper-evidence{padding:24px 0;border-top:1px solid #e2e8ed}.paper-evidence .scope-badge{margin-left:10px}.evidence-links a{overflow-wrap:anywhere;font-size:12px}.evidence-console .quality-note{padding:12px;border-left:3px solid #d9a854;background:#fff9ed}.evidence-console table{width:100%;text-align:left}.evidence-console td,.evidence-console th{padding:12px 9px;border-bottom:1px solid #e2e8ed}.evidence-console .table-wrap{overflow:auto}@media(max-width:750px){.evidence-origins{grid-template-columns:1fr}.audit-stats{gap:18px}.evidence-console .panel-heading{flex-wrap:wrap;gap:12px}}
</style>
