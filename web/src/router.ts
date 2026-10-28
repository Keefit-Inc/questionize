import { createRouter, createWebHistory } from "vue-router";
import SnapPage from "./pages/SnapPage.vue";
import QuestionsPage from "./pages/QuestionsPage.vue";
import QuestionPage from "./pages/QuestionPage.vue";
import MissPage from "./pages/MissPage.vue";
import MePage from "./pages/MePage.vue";
import LegalPage from "./pages/LegalPage.vue";

// Three tabs, as the native app will have: Snap (opens the camera), Questions, Me.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/snap" },
    { path: "/snap", component: SnapPage, meta: { tab: "snap", fullBleed: true } },
    { path: "/questions", component: QuestionsPage, meta: { tab: "questions" } },
    { path: "/misses/:id(\\d+)", component: MissPage, props: (route) => ({ id: Number(route.params.id) }), meta: { tab: "questions" } },
    { path: "/q/:id", component: QuestionPage, props: true, meta: { tab: "questions" } },
    { path: "/me", component: MePage, meta: { tab: "me" } },
    { path: "/privacy", component: LegalPage, props: { doc: "privacy" }, meta: { tab: "me" } },
    { path: "/terms", component: LegalPage, props: { doc: "terms" }, meta: { tab: "me" } },
    { path: "/data-deletion", component: LegalPage, props: { doc: "deletion" }, meta: { tab: "me" } },
    // Earlier addresses.
    { path: "/error-log", redirect: "/questions" },
    { path: "/error-log/new", redirect: "/snap" },
    { path: "/error-log/:id(\\d+)", redirect: (to) => `/misses/${to.params.id}` },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
