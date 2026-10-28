// Settings and the device token, kept in extension storage.
import type { Difficulty, QuestionType } from "@questionize/shared";

export const DEFAULT_SERVER = "https://questionize.org";

export interface Settings {
  server: string;
  types: QuestionType[];
  difficulty: Difficulty;
  count: number;
}

const DEFAULTS: Settings = { server: DEFAULT_SERVER, types: ["CR", "RC"], difficulty: "medium", count: 1 };

export async function loadSettings(): Promise<Settings> {
  const stored = (await chrome.storage.sync.get("settings")).settings as Partial<Settings> | undefined;
  return { ...DEFAULTS, ...stored };
}

export async function saveSettings(settings: Settings): Promise<void> {
  await chrome.storage.sync.set({ settings });
}

// Tokens are per server, so switching to a local server doesn't reuse the production identity.
export async function loadToken(server: string): Promise<string | null> {
  const tokens = ((await chrome.storage.local.get("tokens")).tokens ?? {}) as Record<string, string>;
  return tokens[server] ?? null;
}

export async function saveToken(server: string, token: string): Promise<void> {
  const tokens = ((await chrome.storage.local.get("tokens")).tokens ?? {}) as Record<string, string>;
  await chrome.storage.local.set({ tokens: { ...tokens, [server]: token } });
}
