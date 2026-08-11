// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { homepage } from "../src/lib/homepage.ts";
import { LOCALES } from "../src/lib/locales.ts";

test("freezes the exact English Creator and user narrative", () => {
  const content = homepage("en");
  assert.equal(content.title, "Write it once. Sell it forever.");
  assert.equal(content.lead, "Build an assistant, pass review, publish it. Every team that installs it pays you.");
  assert.deepEqual(content.developerFeatures, [
    { title: "Spec and review", body: "Every assistant follows a strict standard and is manually validated before it ships." },
    { title: "Billing built in", body: "Installs are metered and paid out. You write code, not invoices." },
    { title: "Isolated runtime", body: "Each assistant runs in its own container. No shared state, no surprises." },
  ]);
  assert.equal(content.usersBody, "Create a team, install the assistants it needs, and talk to it in chat — the way you'd talk to people.");
  assert.deepEqual(content.userFeatures, [
    { title: "Reviewed, not generated", body: "Assistants are real code, vetted before publishing. Nothing is written on the fly." },
    { title: "Isolated teams", body: "Each team runs separately, with its own assistants and its own context." },
    { title: "Self-hosted", body: "Runs on your own infrastructure. Your data stays with you." },
  ]);
});

test("provides a complete native homepage narrative for every supported locale", () => {
  const english = homepage("en");
  for (const locale of LOCALES) {
    const content = homepage(locale);
    assert.equal(content.developerFeatures.length, 3);
    assert.equal(content.userFeatures.length, 3);
    for (const value of [
      content.seoTitle,
      content.seoDescription,
      content.title,
      content.lead,
      content.readSpec,
      content.browseAssistants,
      content.developersHeading,
      content.developersBody,
      content.developersCta,
      content.catalogHeading,
      content.catalogUnavailable,
      content.catalogRetry,
      content.usersHeading,
      content.usersBody,
      ...content.developerFeatures.flatMap(({ title, body }) => [title, body]),
      ...content.userFeatures.flatMap(({ title, body }) => [title, body]),
    ]) {
      assert.ok(value.trim().length > 0, `${locale} homepage copy is complete`);
    }
    if (locale !== "en") {
      assert.notEqual(content.title, english.title, `${locale} does not reuse the English headline`);
      assert.notEqual(content.lead, english.lead, `${locale} does not reuse the English lead`);
      assert.notEqual(content.developersBody, english.developersBody, `${locale} localizes the developer narrative`);
      assert.notEqual(content.usersBody, english.usersBody, `${locale} localizes the user narrative`);
    }
  }
});
