// The web app talks to the Rails API on its own origin, as an anonymous device until sign-in exists.
import { ApiClient, ApiError } from "@questionize/shared";

const TOKEN_KEY = "questionize.token";

function storedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export const api = new ApiClient(window.location.origin, storedToken());

let registering: Promise<void> | null = null;

/** Registers an anonymous device on first use; later calls reuse the stored token. */
export async function ensureDevice(): Promise<ApiClient> {
  if (storedToken()) return api;
  registering ??= api.registerDevice().then((device) => {
    try {
      localStorage.setItem(TOKEN_KEY, device.token);
    } catch {
      // Private browsing: the token lives for this page only.
    }
    api.setToken(device.token);
  });
  await registering;
  return api;
}

/** Retries once with a fresh device if the stored token was rejected. */
export async function withDevice<T>(call: (client: ApiClient) => Promise<T>): Promise<T> {
  try {
    return await call(await ensureDevice());
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 401)) throw e;
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // ignore
    }
    registering = null;
    return call(await ensureDevice());
  }
}
