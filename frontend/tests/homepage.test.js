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

test("preserves the founder's name in the German origin story", () => {
  const origin = institutionalPage("about", "de").sections[1].body;
  assert.match(origin, /Julianos Frau/);
  assert.doesNotMatch(origin, /Julianes Frau/);
});

test("uses the canonical public founder name in every About locale", () => {
  for (const locale of LOCALES) {
    assert.match(institutionalPage("about", locale).lead, /Juliano Amaral Gouveia/);
  }
});

test("scopes homepage and institutional open-source claims to licensed components", () => {
  assert.equal(tr("home_open_source", "en"), "Open-source components");
  for (const locale of LOCALES) {
    const page = institutionalPage("openSource", locale);
    assert.ok(page.sections[0].title.includes("Apache-2.0"), `${locale} names the license scope`);
    assert.doesNotMatch(page.sections[0].body, /\bAccount\b|\bDevelopers\b|\bDocs\b/);
  }
});

test("discloses the exact cookie-free homepage analytics boundary", () => {
  for (const locale of LOCALES) {
    const statement = tr("home_privacy_line", locale);
    assert.match(statement, /Cloudflare Web Analytics/);
    assert.doesNotMatch(statement, /no trackers|sem rastreadores|sin rastreadores|sans traceurs|Keine Tracker/i);
  }
});

test("keeps organization-level open-source claims out of every About locale", () => {
  const retiredClaims = [
    "open-source organization",
    "organização de código aberto",
    "organización de código abierto",
    "organisation open source",
    "Open-Source-Organisation",
    "开源组织",
    "オープンソース組織",
    "منظمة مفتوحة المصدر",
  ];
  for (const locale of LOCALES) {
    const lead = institutionalPage("about", locale).lead;
    for (const claim of retiredClaims) assert.ok(!lead.includes(claim), `${locale} omits ${claim}`);
  }
});
