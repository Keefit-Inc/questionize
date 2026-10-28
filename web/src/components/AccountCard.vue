<script setup lang="ts">
// Sign in with Facebook so the review lists, analyses and ratings follow the learner across
// devices; sign out; delete the account.
import { onMounted, ref } from "vue";
import type { Me } from "@questionize/shared";
import { withDevice, useToken } from "../api";
import { facebook, facebookAccessToken } from "../facebook";

const props = defineProps<{ me: Me }>();
const emit = defineEmits<{ changed: [] }>();
const available = ref(false);
const busy = ref(false);
const message = ref("");
const confirming = ref(false);

onMounted(async () => (available.value = !!(await facebook())));

async function signIn() {
  busy.value = true;
  message.value = "";
  try {
    const token = await facebookAccessToken();
    if (!token) return;
    const res = await withDevice((c) => c.facebookLogin(token));
    useToken(res.token);
    message.value = res.switched ? "Signed in. Your account from another device is now on this one too." : "Signed in. Your questions and ratings now follow you to any device.";
    emit("changed");
  } catch {
    message.value = "Facebook sign-in didn't work. Please try again.";
  } finally {
    busy.value = false;
  }
}

function signOut() {
  window.FB?.logout();
  useToken(null);
  message.value = "Signed out on this device.";
  emit("changed");
}

async function deleteAccount() {
  busy.value = true;
  try {
    await withDevice((c) => c.deleteAccount());
    useToken(null);
    confirming.value = false;
    message.value = "Your account and everything personal in it were deleted.";
    emit("changed");
  } catch {
    message.value = "Couldn't delete the account. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="account">
    <template v-if="props.me.account">
      <div class="who">
        <span class="fb" aria-hidden="true">f</span>
        <span><strong>{{ props.me.account.name || "Signed in" }}</strong><small>Signed in with Facebook · synced across devices</small></span>
      </div>
      <button type="button" class="ghost" @click="signOut">Sign out</button>
    </template>
    <template v-else>
      <p class="pitch"><strong>Keep your progress on every device</strong><span>Right now your misses, analyses and ratings are tied to this device. Sign in to open them anywhere.</span></p>
      <button v-if="available" type="button" class="fb-btn" :disabled="busy" @click="signIn">
        <span class="fb" aria-hidden="true">f</span> Continue with Facebook
      </button>
      <p v-else class="muted">Sign-in is coming soon.</p>
    </template>
    <p v-if="message" class="msg" role="status">{{ message }}</p>
    <div class="links">
      <RouterLink to="/privacy">Privacy</RouterLink> · <RouterLink to="/terms">Terms</RouterLink> ·
      <button v-if="!confirming" type="button" class="link danger" @click="confirming = true">Delete my account</button>
      <span v-else class="confirm">
        Delete everything personal? This can't be undone.
        <button type="button" class="link danger" :disabled="busy" @click="deleteAccount">Delete</button>
        <button type="button" class="link" @click="confirming = false">Cancel</button>
      </span>
    </div>
  </section>
</template>

<style scoped>
.account { display: flex; flex-direction: column; gap: 12px; padding: 16px; margin-bottom: 14px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); }
.who { display: flex; align-items: center; gap: 10px; }
.who span:last-child { display: flex; flex-direction: column; }
.who small, .pitch span { color: var(--muted); font-size: 13px; }
.pitch { margin: 0; display: flex; flex-direction: column; gap: 2px; }
.fb { width: 28px; height: 28px; border-radius: 50%; background: #1877f2; color: #fff; font-weight: 800; font-size: 18px; display: inline-flex; align-items: flex-end; justify-content: center; font-family: Helvetica, Arial, sans-serif; }
.fb-btn { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 12px; border-radius: 12px; border: 0; background: #1877f2; color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
.fb-btn .fb { background: #fff; color: #1877f2; width: 22px; height: 22px; font-size: 15px; }
.fb-btn:disabled { opacity: 0.6; }
.ghost { align-self: flex-start; padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: inherit; font: inherit; font-weight: 600; cursor: pointer; }
.muted { margin: 0; color: var(--muted); font-size: 13px; }
.msg { margin: 0; font-size: 13px; color: var(--good); }
.links { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.links a { color: var(--muted); }
.link { background: none; border: 0; padding: 0; font: inherit; color: var(--muted); text-decoration: underline; cursor: pointer; }
.danger { color: var(--bad); }
.confirm { display: inline-flex; flex-wrap: wrap; gap: 8px; color: var(--fg); }
</style>
