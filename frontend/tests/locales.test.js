// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { isLocale, localeDirection, LOCALES, LOCALE_OPTIONS } from "../src/lib/locales.ts";

test("matches the Local Admin locale contract and keeps Arabic right-to-left", () => {
  assert.deepEqual(LOCALES, ["en", "pt", "es", "zh", "fr", "de", "ja", "ar"]);
  assert.deepEqual(LOCALE_OPTIONS.map(({ code }) => code), LOCALES);
  assert.equal(localeDirection("ar"), "rtl");
  for (const locale of LOCALES.filter((locale) => locale !== "ar")) {
    assert.equal(localeDirection(locale), "ltr");
  }
  assert.equal(isLocale("ja"), true);
  assert.equal(isLocale("xx"), false);
});
