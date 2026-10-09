const ASSISTANT_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const SOURCE_DIGEST_RE = /^sha256:[0-9a-f]{64}$/;
// The Developers catalog contract and the Store backend both admit up to 1,000 public Assistants.
export const MAX_CATALOG_ASSISTANTS = 1000;
// Developers' machine contract, and Team and Brain after it, admit up to 128 Actions per Assistant.
const MAX_ASSISTANT_ACTIONS = 128;
const GITHUB_RE = /^https:\/\/github\.com\/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$/;
const PLATFORM_RE = /^linux\/(?:amd64|arm64)$/;
// The Assistant summary is a short description of at most 80 characters, in every interface language.
const ASSISTANT_SUMMARY_CHARS = 80;
const ACTION_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
// Localized display copy bounds: the Assistant description and one line (Action description, Stored Input label).
const ASSISTANT_DESCRIPTION_CHARS = 500;
const DISPLAY_LINE_CHARS = 120;
const ACTION_EFFECTS = new Set(["read_only", "mutating"]);
const MAX_STORED_INPUTS = 8;
const MAX_LINK_CHARS = 256;
// A Stored Input's help link (Developers manifest `help_url`), the same public-URL grammar at its own bound.
const MAX_HELP_URL_CHARS = 2048;
// The Team HTTP protocol's help-URL grammar: one canonical public https URL with a path, an optional query, and no
// port, credentials, fragment, or dot segment, on a lowercase DNS host that is not an IP, IDN, or reserved name.
const PUBLIC_URL_RE = new RegExp(
  "^https://(?=[^/]{1,253}/)" +
    "(?![^/]*\\.(?:arpa|example|home|internal|invalid|lan|local|localdomain|localhost|onion|test)/)" +
    "(?:(?!xn--)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+(?!xn--)[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?" +
    "(?:/(?!\\.\\.?(?:/|\\?|(?![\\s\\S])))(?:[A-Za-z0-9._~!$&()*+,;=:@-]|%(?!2E)[0-9A-F]{2})*)+" +
    "(?:\\?(?:[A-Za-z0-9._~!$&()*+,;=:@/?-]|%[0-9A-F]{2})+)?(?![\\s\\S])",
);
// Creator links by kind, each with the exact https origins it admits; `site` admits any public URL host.
const LINK_PREFIXES = new Map([
  ["site", ["https://"]],
  ["github", ["https://github.com/"]],
  ["x", ["https://x.com/"]],
  ["youtube", ["https://youtube.com/", "https://www.youtube.com/"]],
  ["linkedin", ["https://linkedin.com/", "https://www.linkedin.com/"]],
  ["instagram", ["https://instagram.com/", "https://www.instagram.com/"]],
]);
const HUMAN_REQUEST_KINDS = new Set([
  "approval",
  "input:text",
  "input:textarea",
  "input:password",
  "input:phone",
  "input:select",
  "input:choice",
  "input:choices",
  "auth:password",
  "auth:totp",
  "auth:passkey",
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
  "description",
  "links",
  "stored_inputs",
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
  // Every bound counts Unicode code points, as the producer protocols do, never UTF-16 code units.
  return typeof value === "string" &&
    [...value].length <= maximum &&
    (allowEmpty || value.length > 0) &&
    value.trim() === value &&
    !/[\u0000-\u001f\u007f]/u.test(value);
}

/**
 * One localized display text as Team admits it: bounded, trimmed, printable (no control, format, surrogate,
 * private-use, or unassigned character, and no separator but the ASCII space), and NFC.
 * @param {unknown} value
 * @param {number} maximum
 */
function displayText(value, maximum) {
  return boundedText(value, maximum) &&
    !/[\p{C}\p{Zl}\p{Zp}]|(?! )\p{Zs}/u.test(/** @type {string} */ (value)) &&
    value === /** @type {string} */ (value).normalize("NFC");
}

/** @param {unknown} value */
function validLinks(value) {
  return isObject(value) && Object.entries(value).every(([kind, url]) => {
    const prefixes = LINK_PREFIXES.get(kind);
    return prefixes !== undefined &&
      typeof url === "string" &&
      url.length <= MAX_LINK_CHARS &&
      PUBLIC_URL_RE.test(url) &&
      prefixes.some((prefix) => url.startsWith(prefix));
  });
}

/** @param {unknown} value */
function validStoredInputs(value) {
  return Array.isArray(value) && value.length <= MAX_STORED_INPUTS &&
    value.every((input) =>
      hasExactKeys(input, ["id", "label", "description", "help_url"]) &&
      boundedText(input.id, 64) &&
      ACTION_ID_RE.test(input.id) &&
      displayText(input.label, DISPLAY_LINE_CHARS) &&
      displayText(input.description, ASSISTANT_DESCRIPTION_CHARS) &&
      typeof input.help_url === "string" &&
      input.help_url.length <= MAX_HELP_URL_CHARS &&
      PUBLIC_URL_RE.test(input.help_url)
    ) &&
    new Set(value.map((input) => input.id)).size === value.length;
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
  return Array.isArray(value) && value.length >= 1 && value.length <= MAX_ASSISTANT_ACTIONS && value.every((action) =>
    hasExactKeys(action, ["human_requests", "integrations", "id", "effect", "description"]) &&
    boundedText(action.id, 64) &&
    ACTION_ID_RE.test(action.id) &&
    typeof action.effect === "string" &&
    ACTION_EFFECTS.has(action.effect) &&
    displayText(action.description, DISPLAY_LINE_CHARS) &&
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
    !boundedText(record.summary, ASSISTANT_SUMMARY_CHARS) ||
    !displayText(record.description, ASSISTANT_DESCRIPTION_CHARS) ||
    !validLinks(record.links) ||
    !validStoredInputs(record.stored_inputs) ||
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

/**
 * Parse the catalog for exactly the requested interface language. The display copy is localized from each
 * publication's own language pack; a catalog in any other language is refused so no cache can mix them. The
 * Store admits the description, Creator links, Action effects and descriptions, and Stored Input labels but does
 * not display them.
 * @param {unknown} value
 * @param {string} locale
 */
export function parseAssistantCatalog(value, locale) {
  if (!isObject(value)) throw new Error("invalid Assistant catalog");
  const record = value;
  if (
    !hasExactKeys(record, ["assistants", "locale", "version"]) ||
    record.version !== 1 ||
    typeof locale !== "string" ||
    record.locale !== locale ||
    !Array.isArray(record.assistants)
  ) {
    throw new Error("invalid Assistant catalog");
  }
  if (record.assistants.length > MAX_CATALOG_ASSISTANTS) throw new Error("Assistant catalog is too large");
  const assistants = record.assistants.map(parseAssistant);
  if (new Set(assistants.map((assistant) => assistant.id)).size !== assistants.length) {
    throw new Error("duplicate Assistant catalog entry");
  }
  return Object.freeze(assistants);
}

/**
 * Fetch the public catalog in one interface language; the Store backend admits only its closed locale set.
 * @param {typeof fetch} fetcher
 * @param {string} locale
 */
export async function fetchAssistantCatalog(fetcher, locale) {
  const response = await fetcher(`/api/assistants?locale=${encodeURIComponent(locale)}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return parseAssistantCatalog(await response.json(), locale);
}
