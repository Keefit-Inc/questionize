// Horizontal swipes on a page section: left and right callbacks, ignoring vertical scrolls and
// swipes that start inside something that scrolls sideways or takes text.
import { onBeforeUnmount, watch, type Ref } from "vue";

export function useSwipe(target: Ref<HTMLElement | null>, handlers: { left?: () => void; right?: () => void }) {
  let x = 0;
  let y = 0;
  let tracking = false;

  const start = (e: TouchEvent) => {
    const el = e.target as HTMLElement;
    tracking = e.touches.length === 1 && !el.closest("input, textarea, select, [data-no-swipe]");
    x = e.touches[0].clientX;
    y = e.touches[0].clientY;
  };
  const end = (e: TouchEvent) => {
    if (!tracking) return;
    tracking = false;
    const dx = e.changedTouches[0].clientX - x;
    const dy = e.changedTouches[0].clientY - y;
    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    (dx < 0 ? handlers.left : handlers.right)?.();
  };

  // The element may appear later (after data loads) or be replaced; follow it.
  const detach = (el: HTMLElement | null | undefined) => {
    el?.removeEventListener("touchstart", start);
    el?.removeEventListener("touchend", end);
  };
  watch(
    target,
    (el, old) => {
      detach(old);
      el?.addEventListener("touchstart", start, { passive: true });
      el?.addEventListener("touchend", end, { passive: true });
    },
    { immediate: true },
  );
  onBeforeUnmount(() => detach(target.value));
}
