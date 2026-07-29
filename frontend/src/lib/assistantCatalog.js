const ASSISTANT_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const SOURCE_DIGEST_RE = /^sha256:[0-9a-f]{64}$/;
const PLATFORM_RE = /^linux\/(?:amd64|arm64)$/;
const EXPECTED_ASSISTANT_KEYS = Object.freeze([
  "accounts",
  "allowed_hosts",
  "assistant_id",
  "assistant_version",
  "creators",
  "github",
  "name",
  "platforms",
  "powers",
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
function validAccounts(value) {
  return Array.isArray(value) && value.length <= 32 && value.every((account) =>
    hasExactKeys(account, ["id", "provider", "scopes"]) &&
    boundedText(account.id, 80) &&
    boundedText(account.provider, 80) &&
    boundedStrings(account.scopes, 64, 160)
  );
}

/** @param {unknown} value */
function validPowers(value) {
  return Array.isArray(value) && value.length <= 128 && value.every((power) =>
    hasExactKeys(power, ["accounts", "id"]) &&
    boundedText(power.id, 80) &&
    boundedStrings(power.accounts, 32, 80)
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
    !boundedText(record.github, 500) ||
    typeof record.source_digest !== "string" ||
    !SOURCE_DIGEST_RE.test(record.source_digest) ||
    !boundedStrings(record.creators, 16, 80) ||
    !boundedStrings(record.platforms, 2, 20, PLATFORM_RE) ||
    !boundedStrings(record.allowed_hosts, 64, 253) ||
    !validAccounts(record.accounts) ||
    !validPowers(record.powers)
  ) {
    throw new Error("invalid Assistant catalog");
  }
  return Object.freeze({
    id: record.assistant_id,
    name: record.name,
    summary: record.summary,
    version: record.assistant_version,
    creators: Object.freeze([...(/** @type {string[]} */ (record.creators))]),
    sourceDigest: record.source_digest,
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
