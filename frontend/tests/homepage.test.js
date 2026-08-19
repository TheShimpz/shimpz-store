// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { homepage } from "../src/lib/homepage.ts";
import { institutionalPage } from "../src/lib/institutional.ts";
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
  assert.equal(tr("assistants_free", "es"), "Free");
  assert.equal(tr("missing_translation", "en"), "missing_translation");
});

test("describes only current Assistant behavior", () => {
  for (const locale of LOCALES) {
    assert.doesNotMatch(tr("assistants_lead", locale), /routine|rotina/i);
  }
});

test("lists the CLI in every localized open-source repository map", () => {
  for (const locale of LOCALES) {
    const repositories = institutionalPage("openSource", locale).sections[0];
    assert.ok(repositories.body.includes("CLI"), `${locale} includes the CLI repository`);
  }
});
