const ASSISTANT_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const SOURCE_DIGEST_RE = /^sha256:[0-9a-f]{64}$/;
const GITHUB_RE = /^https:\/\/github\.com\/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$/;
const PLATFORM_RE = /^linux\/(?:amd64|arm64)$/;
const ACTION_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const HUMAN_REQUEST_KINDS = new Set([
  "approval",
  "input:text",
  "input:textarea",
  "input:password",
  "input:phone",
  "input:select",
  "input:choice",
  "input:choices",
  "auth:reauth",
  "auth:second-factor",
  "auth:phishing-resistant",
]);
const EXPECTED_ASSISTANT_KEYS = Object.freeze([
  "integrations",
  "allowed_hosts",
  "assistant_id",
  "assistant_version",
  "creators",
  "github",
  "icon_digest",
  "name",
  "platforms",
  "actions",
  "source_digest",
  "summary",
]);

/** @param {unknown} value @returns {value is Record<string, unknown>} */
function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** @param {unknown} value @param {readonly string[]} expected */
function hasExactKeys(value, expected) {
  return isObject(value) &&
    Object.keys(value).sort().join("\0") === [...expected].sort().join("\0");
}

/**
 * @param {unknown} value
 * @param {number} maximum
 * @param {boolean} [allowEmpty]
 * @returns {value is string}
 */
function boundedText(value, maximum, allowEmpty = false) {
  return typeof value === "string" &&
    value.length <= maximum &&
    (allowEmpty || value.length > 0) &&
    value.trim() === value &&
    !/[\u0000-\u001f\u007f]/u.test(value);
}

/**
 * @param {unknown} value
 * @param {number} maximumItems
 * @param {number} maximumLength
 * @param {RegExp | null} [pattern]
 */
function boundedStrings(value, maximumItems, maximumLength, pattern = null) {
  if (!Array.isArray(value) || value.length > maximumItems) return false;
  const seen = new Set();
  for (const item of value) {
    if (!boundedText(item, maximumLength) || (pattern && !pattern.test(item)) || seen.has(item)) {
      return false;
    }
    seen.add(item);
  }
  return true;
}

/** @param {unknown} value */
function validIntegrations(value) {
  return Array.isArray(value) && value.length <= 32 && value.every((integration) =>
    hasExactKeys(integration, ["id", "provider", "scopes"]) &&
    boundedText(integration.id, 80) &&
    boundedText(integration.provider, 80) &&
    boundedStrings(integration.scopes, 64, 160)
  );
}

/** @param {unknown} value */
function validActions(value) {
  return Array.isArray(value) && value.length >= 1 && value.length <= 64 && value.every((action) =>
    hasExactKeys(action, ["human_requests", "integrations", "id"]) &&
    boundedText(action.id, 64) &&
    ACTION_ID_RE.test(action.id) &&
    boundedStrings(action.integrations, 16, 64) &&
    boundedStrings(action.human_requests, 11, 25) &&
    (/** @type {string[]} */ (action.human_requests)).every((kind) => HUMAN_REQUEST_KINDS.has(kind))
  );
}

/** @param {unknown} value */
function parseAssistant(value) {
  if (!isObject(value)) throw new Error("invalid Assistant catalog");
  const record = value;
  if (
    !hasExactKeys(record, EXPECTED_ASSISTANT_KEYS) ||
    !boundedText(record.assistant_id, 80) ||
    !ASSISTANT_ID_RE.test(record.assistant_id) ||
    !boundedText(record.name, 160) ||
    !boundedText(record.summary, 500) ||
    !boundedText(record.assistant_version, 80) ||
    typeof record.github !== "string" ||
    !GITHUB_RE.test(record.github) ||
    typeof record.source_digest !== "string" ||
    !SOURCE_DIGEST_RE.test(record.source_digest) ||
    typeof record.icon_digest !== "string" ||
    !SOURCE_DIGEST_RE.test(record.icon_digest) ||
    !boundedStrings(record.creators, 16, 80) ||
    !boundedStrings(record.platforms, 2, 20, PLATFORM_RE) ||
    !boundedStrings(record.allowed_hosts, 64, 253) ||
    !validIntegrations(record.integrations) ||
    !validActions(record.actions)
  ) {
    throw new Error("invalid Assistant catalog");
  }
  const providers = [...new Set(
    (/** @type {{ provider: string }[]} */ (record.integrations)).map(({ provider }) => provider),
  )].sort((left, right) => left.localeCompare(right, "en"));
  const integrations = (/** @type {{ id: string, provider: string, scopes: string[] }[]} */ (record.integrations))
    .map(({ id, provider, scopes }) => Object.freeze({ id, provider, scopes: Object.freeze([...scopes]) }));
  const actions = (/** @type {{ id: string, integrations: string[], human_requests: string[] }[]} */ (record.actions))
    .map(({ id, integrations: actionIntegrations, human_requests: humanRequests }) => Object.freeze({
      id,
      integrations: Object.freeze([...actionIntegrations]),
      humanRequests: Object.freeze([...humanRequests]),
    }));
  return Object.freeze({
    id: record.assistant_id,
    name: record.name,
    summary: record.summary,
    version: record.assistant_version,
    creators: Object.freeze([...(/** @type {string[]} */ (record.creators))]),
    providers: Object.freeze(providers),
    github: record.github,
    platforms: Object.freeze([...(/** @type {string[]} */ (record.platforms))]),
    allowedHosts: Object.freeze([...(/** @type {string[]} */ (record.allowed_hosts))]),
    integrations: Object.freeze(integrations),
    actions: Object.freeze(actions),
    sourceDigest: record.source_digest,
    iconDigest: record.icon_digest,
  });
}

/** @param {unknown} value */
export function parseAssistantCatalog(value) {
  if (!isObject(value)) throw new Error("invalid Assistant catalog");
  const record = value;
  if (!hasExactKeys(record, ["assistants", "version"]) || record.version !== 1 || !Array.isArray(record.assistants)) {
    throw new Error("invalid Assistant catalog");
  }
  if (record.assistants.length > 256) throw new Error("Assistant catalog is too large");
  const assistants = record.assistants.map(parseAssistant);
  if (new Set(assistants.map((assistant) => assistant.id)).size !== assistants.length) {
    throw new Error("duplicate Assistant catalog entry");
  }
  return Object.freeze(assistants);
}
