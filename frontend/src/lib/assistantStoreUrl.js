import { LOCALES } from "./locales.ts";

const ASSISTANT_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
/** @type {Set<string>} */
const STORE_LOCALES = new Set(LOCALES);

/** @param {unknown} locale @param {unknown} assistant */
export function closedAssistantStoreHref(locale, assistant) {
  if (typeof locale !== "string" || typeof assistant !== "string" || !STORE_LOCALES.has(locale) || !ASSISTANT_ID_RE.test(assistant)) {
    throw new Error("invalid Assistant Store destination");
  }
  return `/${locale}/assistants?assistant=${encodeURIComponent(assistant)}`;
}

/** @param {unknown} search @returns {string} */
export function requestedAssistantFromSearch(search) {
  if (typeof search !== "string") return "";
  const params = new URLSearchParams(search);
  const keys = [...params.keys()];
  if (keys.length !== 1 || keys[0] !== "assistant") return "";
  const assistant = params.get("assistant");
  return assistant !== null && ASSISTANT_ID_RE.test(assistant) ? assistant : "";
}
