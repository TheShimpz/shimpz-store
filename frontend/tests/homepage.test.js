// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { homepage } from "../src/lib/homepage.ts";
import { LOCALES } from "../src/lib/locales.ts";
import { tr } from "../src/lib/i18n.ts";

test("freezes the exact first-person English homepage narrative", () => {
  const content = homepage("en");
  assert.deepEqual(content.title, {
    accent: "I do the work",
    remainder: "so you can",
    secondLine: "focus on what matters.",
  });
});

test("provides a complete native homepage narrative for every supported locale", () => {
  const english = homepage("en");
  for (const locale of LOCALES) {
    const content = homepage(locale);
    for (const value of [
      content.seoTitle,
      content.seoDescription,
      content.title.accent,
      content.title.secondLine,
    ]) {
      assert.ok(value.trim().length > 0, `${locale} homepage copy is complete`);
    }
    if (locale !== "en") {
      assert.notEqual(content.title.accent, english.title.accent, `${locale} localizes the highlighted headline phrase`);
    }
  }
});

test("falls back only through the explicit translation chain", () => {
  assert.equal(tr("close", "es"), "Close");
  assert.equal(tr("missing_translation", "en"), "missing_translation");
});
