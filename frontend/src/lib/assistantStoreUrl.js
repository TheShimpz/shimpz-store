import { isAssistantId } from "./assistantCatalog.js";
import { LOCALES } from "./locales.ts";

/** @type {Set<string>} */
const STORE_LOCALES = new Set(LOCALES);

/** @param {unknown} locale @param {unknown} assistant */
export function closedAssistantStoreHref(locale, assistant) {
  if (typeof locale !== "string" || !STORE_LOCALES.has(locale) || !isAssistantId(assistant)) {
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
  return isAssistantId(assistant) ? assistant : "";
}
