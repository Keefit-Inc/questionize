<script setup lang="ts">
// Privacy policy, terms of use and data deletion instructions. Plain text in templates, kept in
// step with what the code actually does (docs/KNOWLEDGE_MODEL.md §9, docs/ARCHITECTURE.md §5.7).
import { computed } from "vue";
import { useRoute } from "vue-router";

const props = defineProps<{ doc: "privacy" | "terms" | "deletion" }>();
const route = useRoute();
const code = computed(() => (typeof route.query.code === "string" ? route.query.code.replace(/[^a-f0-9]/gi, "").slice(0, 32) : ""));
const CONTACT = "privacy@questionize.org";
const UPDATED = "October 29, 2026";
</script>

<template>
  <article class="legal">
    <template v-if="props.doc === 'privacy'">
      <h1 class="page-title">Privacy Policy</h1>
      <p class="meta">Last updated {{ UPDATED }} · Questionize is operated by Keefit, Inc.</p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>A device account.</strong> When you first open Questionize we create an anonymous account with a random identifier. No name or email is needed.</li>
        <li><strong>Your practice.</strong> The answers you choose, how long you take, your ratings and XP, and the votes, reports and comments you leave on questions.</li>
        <li><strong>Questions you snap.</strong> Where the question is (the book, page and number you type, if any), the answer you chose, and our analysis of it. Your photos are read once and deleted; we keep no copy. The words of the question are sent once to your device so you can solve it again, and then deleted from our servers.</li>
        <li><strong>Eligibility.</strong> The country you tell us and your confirmation that you are 13 or older.</li>
        <li><strong>If you sign in with Facebook.</strong> Your Facebook user ID for this app, your name, and your email if you allow it. We do not store your Facebook password or access token, and we do not post to Facebook for you.</li>
        <li><strong>Pages you share.</strong> When you share a question to another service, that service's own policy applies to what you post.</li>
      </ul>

      <h2>How we use it</h2>
      <ul>
        <li>To run Questionize: show you questions, rate your answers, analyze the questions you snap, and keep your review lists.</li>
        <li>To improve questions: answer patterns and reports help us find and fix weak questions.</li>
        <li>To build statistics. We combine answers from many learners into de-identified, aggregate statistics, such as how hard a question is, how often each option is chosen, and which reasoning mistakes are common. Keefit, Inc. may use these statistics in its products and may license them to others. They do not identify you.</li>
        <li>The abstract design of a question you snap (what it tests and which traps it uses, never its wording) can become part of our knowledge model and help write new questions for everyone.</li>
      </ul>

      <h2>Who processes it</h2>
      <p>Photos and question text are analyzed by AI models from our model providers (including Meta's model service) under their terms for business use. Our servers are run by our hosting provider. These providers process data only to provide their service to us.</p>

      <h2>What we don't do</h2>
      <ul>
        <li>We do not sell your personal information.</li>
        <li>We do not show ads or use your data to target ads.</li>
        <li>We do not publish anything from the books you photograph.</li>
      </ul>

      <h2>Age</h2>
      <p>Questionize is not for children under 13. Photo analysis (Snap) is available in the United States to people 13 and older.</p>

      <h2>Keeping and deleting your data</h2>
      <p>
        We keep your data while your account exists. You can delete your account at any time under Me → Delete my account. If you signed in with Facebook, you can also remove
        Questionize in your Facebook settings (Settings &amp; privacy → Apps and websites), which asks us to delete your data. When an account is deleted, everything personal in it is
        removed. Questions written for the shared bank stay there, because they contain nothing about you, and answers already counted in a question's statistics stay as anonymous counts.
      </p>

      <h2>Contact</h2>
      <p>Questions or requests: <span class="addr">{{ CONTACT }}</span></p>
    </template>

    <template v-else-if="props.doc === 'terms'">
      <h1 class="page-title">Terms of Use</h1>
      <p class="meta">Last updated {{ UPDATED }} · Questionize is operated by Keefit, Inc.</p>

      <h2>Using Questionize</h2>
      <p>Questionize is free to use for your own study. You must be at least 13. Ratings in Questionize are a practice scale, not official test scores.</p>

      <h2>Questions you snap</h2>
      <p>
        Only photograph material you own or may use, one question at a time, for your own study. Do not upload questions from a live or recent exam. We read your photo once and
        delete it; the question's words are kept only on your device.
      </p>

      <h2>Shared questions</h2>
      <p>
        Questions in the shared bank are offered under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 license, to the extent they are protected: you may share and adapt
        them for non-commercial purposes with attribution to Questionize. Questions published before October 29, 2026 remain under CC BY-SA 4.0. Commercial use, including printed or
        sold workbooks and use in paid products, needs a license from Keefit, Inc.
      </p>

      <h2>Data and access</h2>
      <p>
        Question statistics, difficulty calibration, the knowledge model's measurements and learners' results are not licensed for reuse. Do not scrape, bulk-download or copy them
        from the service, and do not use automated access except through an API we offer for that purpose and under its terms.
      </p>

      <h2>What you contribute</h2>
      <p>
        You give Keefit, Inc. a worldwide, perpetual, royalty-free license to use the votes, reports, comments and corrections you submit, including in commercial products, so the
        bank can keep improving. You keep any rights you have in them.
      </p>

      <h2>The service</h2>
      <p>
        Questionize uses AI to write and check questions; it can make mistakes, and it is provided as is, without warranties. We may change or stop parts of the service. We may
        suspend accounts that break these terms. The source code is open under the MIT license; these terms cover the service at questionize.org.
      </p>

      <h2>Contact</h2>
      <p><span class="addr">{{ CONTACT }}</span></p>
    </template>

    <template v-else>
      <h1 class="page-title">Delete your data</h1>
      <p v-if="code" class="done">Your deletion request was received and completed. Confirmation code: <code>{{ code }}</code></p>
      <h2>From Questionize</h2>
      <p>Open Me → Delete my account. Your account and everything personal in it are deleted right away.</p>
      <h2>From Facebook</h2>
      <p>If you signed in with Facebook, go to Facebook Settings &amp; privacy → Settings → Apps and websites, remove Questionize, and choose to delete your data. Facebook tells us, and we delete your account.</p>
      <h2>What stays</h2>
      <p>Questions written for the shared bank contain nothing about you and stay there. Answers already counted in a question's statistics stay as anonymous counts.</p>
      <p>Questions: <span class="addr">{{ CONTACT }}</span></p>
    </template>
  </article>
</template>

<style scoped>
.legal { max-width: 40rem; padding-bottom: 24px; line-height: 1.6; }
.meta { margin: -6px 0 14px; color: var(--muted); font-size: 13px; }
h2 { margin: 22px 0 6px; font-size: 16px; }
p, li { color: var(--fg); }
ul { padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
.addr { font-weight: 600; user-select: all; }
.done { padding: 12px 14px; border-radius: 12px; background: var(--good-soft); color: var(--good); }
code { font-size: 13px; }
</style>
