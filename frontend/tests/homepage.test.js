// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { formatCatalogCount, homepage } from "../src/lib/homepage.ts";
import { LOCALES } from "../src/lib/locales.ts";

test("freezes the exact first-person English homepage narrative", () => {
  const content = homepage("en");
  assert.equal(content.title, "Give me a goal and my assistants do the work on your computer");
  assert.equal(content.lead, "No agents. No code. Just a team. Assistants that already work — with the LLM you choose.");
  assert.equal(content.demoCaption, '"Build me a landing page inspired by Apple." — so I did.');
  assert.equal(content.usersHeading, "What I do for you");
  assert.equal(content.usersBody, "Give me a goal and I'll put the right assistants on it. I orchestrate, they execute — all on your machine.");
  assert.deepEqual(content.userFeatures, [
    { title: "I don't improvise", body: "Every assistant I use follows a strict spec and is manually reviewed before it ships. Nothing is generated at runtime." },
    { title: "I keep teams apart", body: "Each team runs in its own containers, with its own assistants and its own context." },
    { title: "I run where you are", body: "Self-hosted, with the LLM you choose. Your data never leaves your machine." },
  ]);
  assert.equal(content.developersHeading, "Build one I can use");
  assert.equal(content.developersBody, "Write your assistant once, against a strict spec. Pass review, publish it, and get paid every time a team installs it. Users never touch your code — I handle the orchestration.");
  assert.deepEqual(content.developerFeatures, [
    { title: "Spec and review", body: "A strict standard and manual validation before anything ships." },
    { title: "Billing built in", body: "Installs are metered and paid out." },
    { title: "Isolated runtime", body: "Your assistant runs in its own container. No infra to manage." },
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
      content.meetAssistants,
      content.watchMeWork,
      content.demoCaption,
      content.demoPending,
      content.developersHeading,
      content.developersBody,
      content.developersCta,
      content.catalogHeading,
      content.assistantZero,
      content.assistantSingular,
      content.assistantPlural,
      content.catalogCountTemplate,
      content.catalogCountZeroTemplate,
      content.catalogCountSingularTemplate,
      content.catalogCore,
      content.catalogUnavailable,
      content.catalogRetry,
      content.catalogCta,
      content.usersHeading,
      content.usersBody,
      ...content.developerFeatures.flatMap(({ title, body }) => [title, body]),
      ...content.userFeatures.flatMap(({ title, body }) => [title, body]),
    ]) {
      assert.ok(value.trim().length > 0, `${locale} homepage copy is complete`);
    }
    assert.ok(content.catalogCountTemplate.includes("{count}"), `${locale} catalog count retains {count}`);
    assert.ok(content.catalogCountTemplate.includes("{noun}"), `${locale} catalog count retains {noun}`);
    assert.ok(content.catalogCountZeroTemplate.includes("{count}"), `${locale} zero catalog count retains {count}`);
    assert.ok(content.catalogCountZeroTemplate.includes("{noun}"), `${locale} zero catalog count retains {noun}`);
    assert.ok(content.catalogCountSingularTemplate.includes("{count}"), `${locale} singular catalog count retains {count}`);
    assert.ok(content.catalogCountSingularTemplate.includes("{noun}"), `${locale} singular catalog count retains {noun}`);
    if (locale !== "en") {
      assert.notEqual(content.title, english.title, `${locale} does not reuse the English headline`);
      assert.notEqual(content.lead, english.lead, `${locale} does not reuse the English lead`);
      assert.notEqual(content.developersBody, english.developersBody, `${locale} localizes the developer narrative`);
      assert.notEqual(content.usersBody, english.usersBody, `${locale} localizes the user narrative`);
    }
  }
});

test("formats catalog counts according to each locale", () => {
  assert.equal(formatCatalogCount(homepage("en"), 0), "0 assistants I can work with");
  assert.equal(formatCatalogCount(homepage("en"), 1), "1 assistant I can work with");
  assert.equal(formatCatalogCount(homepage("es"), 1), "1 asistente con el que puedo trabajar");
  assert.equal(formatCatalogCount(homepage("fr"), 0), "0 assistant avec lequel je peux travailler");
  assert.equal(formatCatalogCount(homepage("fr"), 1), "1 assistant avec lequel je peux travailler");
  assert.equal(formatCatalogCount(homepage("de"), 1), "1 Assistant, mit dem ich arbeiten kann");
  assert.equal(formatCatalogCount(homepage("zh"), 3), "我可以协作的 3个 Assistant");
  assert.equal(formatCatalogCount(homepage("ja"), 1), "私が連携できる 1件の Assistant");
});
