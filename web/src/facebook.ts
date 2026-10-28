// Facebook Login with the JavaScript SDK. The app id comes from the server at runtime, so the
// web app needs no rebuild when it changes; without one, sign-in is simply not offered.
import { api } from "./api";

interface FB {
  init(o: { appId: string; version: string; cookie?: boolean; xfbml?: boolean }): void;
  login(cb: (r: { authResponse?: { accessToken: string } | null; status: string }) => void, o: { scope: string }): void;
  logout(cb?: () => void): void;
}
declare global {
  interface Window {
    FB?: FB;
    fbAsyncInit?: () => void;
  }
}

const VERSION = "v21.0";
let ready: Promise<FB | null> | null = null;

export function facebook(): Promise<FB | null> {
  ready ??= api
    .getConfig()
    .then(({ facebook_app_id }) => {
      if (!facebook_app_id) return null;
      return new Promise<FB | null>((resolve) => {
        window.fbAsyncInit = () => {
          window.FB!.init({ appId: facebook_app_id, version: VERSION, cookie: false, xfbml: false });
          resolve(window.FB!);
        };
        const s = document.createElement("script");
        s.src = "https://connect.facebook.net/en_US/sdk.js";
        s.async = true;
        s.crossOrigin = "anonymous";
        s.onerror = () => resolve(null);
        document.head.appendChild(s);
      });
    })
    .catch(() => null);
  return ready;
}

/** Opens the Facebook Login dialog; resolves with an access token, or null if the learner cancelled. */
export async function facebookAccessToken(): Promise<string | null> {
  const fb = await facebook();
  if (!fb) return null;
  return new Promise((resolve) => fb.login((r) => resolve(r.authResponse?.accessToken ?? null), { scope: "public_profile,email" }));
}
