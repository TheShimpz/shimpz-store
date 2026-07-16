const PROVIDERS = new Set(["claude-code", "codex"]);
const CAPSULE_ID = /^[a-z0-9][a-z0-9_-]{0,127}$/;
const LOGIN_MODES = Object.freeze({ "claude-code": "authorization_code", codex: "device_code" });
const DEVICE_STATES = new Set(["idle", "starting", "waiting", "succeeded", "failed", "cancelled", "timeout"]);

/** @typedef {{ kind: "authorization_code", url: string }} AuthorizationCodeChallenge */
/** @typedef {{ kind: "device", url: string, userCode: string }} DeviceChallenge */
/** @typedef {AuthorizationCodeChallenge | DeviceChallenge} BrainLoginChallenge */

/**
 * Accept only a provider URL that can safely be opened in a new browser tab. Codex follows the
 * OAuth device contract: the browser receives a user code, never a pasted auth.json credential.
 *
 * @param {string} provider
 * @param {unknown} payload
 * @returns {BrainLoginChallenge | null}
 */
export function parseBrainLoginChallenge(provider, payload) {
  if (!PROVIDERS.has(provider) || !payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const value = /** @type {Record<string, unknown>} */ (payload);
  if ("provider" in value && value.provider !== provider) return null;
  if ("mode" in value && value.mode !== LOGIN_MODES[/** @type {keyof typeof LOGIN_MODES} */ (provider)]) return null;
  if (typeof value.url !== "string" || value.url.length > 2048) return null;
  let url;
  try {
    url = new URL(value.url);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) return null;
  if (provider === "codex") {
    const userCode = typeof value.user_code === "string" ? value.user_code : "";
    const parts = userCode.split("-");
    const validCode =
      parts.length >= 2 &&
      parts.length <= 3 &&
      parts.every((part) => /^[A-Z0-9]{4,8}$/.test(part));
    if (
      url.hostname !== "auth.openai.com" ||
      url.pathname.replace(/\/$/, "") !== "/codex/device" ||
      url.search ||
      url.hash ||
      !validCode
    ) return null;
    return { kind: "device", url: url.href, userCode };
  }
  if (url.hostname !== "claude.ai" || url.pathname.replace(/\/$/, "") !== "/oauth/authorize") return null;
  return { kind: "authorization_code", url: url.href };
}

/**
 * @param {string} capsuleId
 * @returns {{ start: string, challenge: string, code: string, status: string, cancel: string }}
 */
export function brainLoginEndpoints(capsuleId) {
  if (!CAPSULE_ID.test(capsuleId)) throw new Error("Invalid Capsule login context.");
  const base = `/api/capsules/${encodeURIComponent(capsuleId)}/brain/login`;
  return {
    start: `${base}/start`,
    challenge: `${base}/url`,
    code: `${base}/code`,
    status: `${base}/status`,
    cancel: `${base}/cancel`,
  };
}

/**
 * @param {unknown} payload
 * @returns {{ loggedIn: boolean, lastError: string, state: string }}
 */
export function parseBrainLoginStatus(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { loggedIn: false, lastError: "", state: "" };
  }
  const value = /** @type {Record<string, unknown>} */ (payload);
  return {
    loggedIn: value.loggedIn === true,
    lastError: typeof value.last_error === "string" ? value.last_error.slice(0, 300) : "",
    state: typeof value.state === "string" && DEVICE_STATES.has(value.state) ? value.state : "",
  };
}
