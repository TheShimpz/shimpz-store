const BASE64URL_RE = /^[A-Za-z0-9_-]{1,4096}$/;
const HANDLE_RE = /^[A-Za-z0-9_-]{43}$/;
const TEAM_ID_RE = /^[a-z0-9_]{1,40}$/;
const CHALLENGE_ID_RE = /^[a-f0-9]{32}$/;
const MAX_ASSURANCE_TTL_SECONDS = 300;

/** @param {any} value */
function record(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value : null;
}

/** @param {Record<string, any>} value @param {string[]} keys */
function hasExactKeys(value, keys) {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

/** @param {any} value @returns {ArrayBuffer} */
export function decodeBase64url(value) {
  if (typeof value !== "string" || !BASE64URL_RE.test(value)) {
    throw new TypeError("invalid base64url value");
  }
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(value.replaceAll("-", "+").replaceAll("_", "/") + padding);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0)).buffer;
}

/** @param {ArrayBuffer} value @returns {string} */
export function encodeBase64url(value) {
  if (!(value instanceof ArrayBuffer) || value.byteLength === 0 || value.byteLength > 4096) {
    throw new TypeError("invalid credential buffer");
  }
  let binary = "";
  for (const byte of new Uint8Array(value)) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

/** @param {any} value @returns {PublicKeyCredentialRequestOptions} */
export function parseActionAssuranceOptions(value) {
  const source = record(value);
  const expected = ["challenge", "timeout", "rpId", "allowCredentials", "userVerification"];
  if (
    !source ||
    !hasExactKeys(source, expected) ||
    !Number.isSafeInteger(source.timeout) ||
    source.timeout < 1 ||
    source.timeout > 300_000 ||
    typeof source.rpId !== "string" ||
    !source.rpId ||
    source.rpId.length > 253 ||
    source.userVerification !== "required" ||
    !Array.isArray(source.allowCredentials) ||
    source.allowCredentials.length < 1 ||
    source.allowCredentials.length > 32
  ) {
    throw new TypeError("invalid passkey options");
  }
  return {
    challenge: decodeBase64url(source.challenge),
    timeout: source.timeout,
    rpId: source.rpId,
    userVerification: "required",
    allowCredentials: source.allowCredentials.map((/** @type {any} */ value) => {
      const descriptor = record(value);
      if (!descriptor || !hasExactKeys(descriptor, ["id", "type"]) || descriptor.type !== "public-key") {
        throw new TypeError("invalid passkey credential descriptor");
      }
      return { id: decodeBase64url(descriptor.id), type: "public-key" };
    }),
  };
}

/** @param {any} value */
export function serializeActionAssuranceCredential(value) {
  if (!(value instanceof PublicKeyCredential) || !(value.response instanceof AuthenticatorAssertionResponse)) {
    throw new TypeError("invalid passkey credential");
  }
  const response = value.response;
  /** @type {Record<string, string>} */
  const projectedResponse = {
    clientDataJSON: encodeBase64url(response.clientDataJSON),
    authenticatorData: encodeBase64url(response.authenticatorData),
    signature: encodeBase64url(response.signature),
  };
  if (response.userHandle) projectedResponse.userHandle = encodeBase64url(response.userHandle);
  return {
    id: value.id,
    rawId: encodeBase64url(value.rawId),
    type: value.type,
    response: projectedResponse,
  };
}

/** @param {any} value @returns {string} */
export function parseActionAssuranceHandle(value) {
  const source = record(value);
  if (
    !source ||
    !hasExactKeys(source, ["version", "handle", "expires_in"]) ||
    source.version !== 1 ||
    typeof source.handle !== "string" ||
    !HANDLE_RE.test(source.handle) ||
    !Number.isSafeInteger(source.expires_in) ||
    source.expires_in < 1 ||
    source.expires_in > MAX_ASSURANCE_TTL_SECONDS
  ) {
    throw new TypeError("invalid Action assurance response");
  }
  return source.handle;
}

/** @param {any} teamId @param {any} challengeId @param {string | null} field @param {any} value */
export function createActionAssuranceBody(teamId, challengeId, field, value) {
  if (
    typeof teamId !== "string" ||
    !TEAM_ID_RE.test(teamId) ||
    typeof challengeId !== "string" ||
    !CHALLENGE_ID_RE.test(challengeId)
  ) {
    throw new TypeError("invalid Action assurance binding");
  }
  /** @type {Record<string, any>} */
  const body = { team_id: teamId, challenge_id: challengeId };
  if (field !== null) {
    if (!["password", "code", "credential"].includes(field)) {
      throw new TypeError("invalid Action assurance factor");
    }
    body[field] = value;
  }
  return body;
}
