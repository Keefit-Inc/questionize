import { createRouter, createWebHistory } from "vue-router";
import FeedPage from "./pages/FeedPage.vue";
import QuestionPage from "./pages/QuestionPage.vue";
import MePage from "./pages/MePage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: FeedPage },
    { path: "/q/:id", component: QuestionPage, props: true },
    { path: "/me", component: MePage },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
