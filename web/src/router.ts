import { createRouter, createWebHistory } from "vue-router";
import FeedPage from "./pages/FeedPage.vue";
import QuestionPage from "./pages/QuestionPage.vue";
import MePage from "./pages/MePage.vue";
import ErrorLogPage from "./pages/ErrorLogPage.vue";
import ErrorLogCapturePage from "./pages/ErrorLogCapturePage.vue";
import ErrorLogEntryPage from "./pages/ErrorLogEntryPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: FeedPage },
    { path: "/q/:id", component: QuestionPage, props: true },
    { path: "/me", component: MePage },
    { path: "/error-log", component: ErrorLogPage },
    { path: "/error-log/new", component: ErrorLogCapturePage },
    { path: "/error-log/:id(\\d+)", component: ErrorLogEntryPage, props: (route) => ({ id: Number(route.params.id) }) },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
