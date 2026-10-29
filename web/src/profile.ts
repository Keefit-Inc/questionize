// The learner's profile, shared by the level sheet, Me and the Bank.
import { ref } from "vue";
import type { LevelId, Me } from "@questionize/shared";
import { withDevice } from "./api";
import { DEFAULT_LEVEL } from "./levels";

export const me = ref<Me | null>(null);

export async function loadMe(): Promise<Me | null> {
  try {
    me.value = await withDevice(async (c) => {
      const profile = await c.getMe();
      if (!profile.level) {
        await c.setLevel(DEFAULT_LEVEL);
        return { ...profile, level: DEFAULT_LEVEL };
      }
      return profile;
    });
  } catch {
    // Offline or the server is down: screens that need it show their own errors.
  }
  return me.value;
}

export async function chooseLevel(level: LevelId) {
  await withDevice((c) => c.setLevel(level));
  if (me.value) me.value = { ...me.value, level };
}
