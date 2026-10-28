// The learner's profile, shared by the level sheet, Me and the Bank.
import { ref } from "vue";
import type { LevelId, Me } from "@questionize/shared";
import { withDevice } from "./api";

export const me = ref<Me | null>(null);

export async function loadMe(): Promise<Me | null> {
  try {
    me.value = await withDevice((c) => c.getMe());
  } catch {
    // Offline or the server is down: screens that need it show their own errors.
  }
  return me.value;
}

export async function chooseLevel(level: LevelId) {
  await withDevice((c) => c.setLevel(level));
  if (me.value) me.value = { ...me.value, level };
}
