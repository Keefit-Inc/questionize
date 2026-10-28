// Installing Questionize to the home screen. Chrome and Edge offer a prompt we can trigger from a
// button; Safari on iPhone and iPad only installs from Share → Add to Home Screen.
import { ref } from "vue";

interface InstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export const installed = ref(
  window.matchMedia?.("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true,
);
export const canPrompt = ref(false);
export const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
let deferred: InstallPromptEvent | null = null;

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferred = e as InstallPromptEvent;
  canPrompt.value = true;
});
window.addEventListener("appinstalled", () => {
  installed.value = true;
  canPrompt.value = false;
});

export async function promptInstall(): Promise<void> {
  if (!deferred) return;
  await deferred.prompt();
  const { outcome } = await deferred.userChoice;
  if (outcome === "accepted") installed.value = true;
  deferred = null;
  canPrompt.value = false;
}

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || !import.meta.env.PROD) return;
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => undefined));
}
