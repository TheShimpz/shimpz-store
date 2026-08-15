// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  formatCatalogCount,
  homepage,
  HOMEPAGE_TASK_HOLD_MS,
  HOMEPAGE_TASK_TYPING_DELAY_MS,
} from "../src/lib/homepage.ts";
import { LOCALES } from "../src/lib/locales.ts";
import { humanRequestContextParts } from "../src/lib/humanRequestContext.ts";
import { tr } from "../src/lib/i18n.ts";

test("freezes the exact first-person English homepage narrative", () => {
  const content = homepage("en");
  assert.equal(content.intro, "Hello, I'm Shimpz!");
  assert.equal(content.title, "I do the work so you can focus on what matters.");
  assert.equal(content.lead, "Type your first task below and see what I can do:");
  assert.equal(content.taskPlaceholder, "Describe the result you need...");
  assert.deepEqual(content.taskExamples, [
    "Turn these campaign results into my next actions...",
    "Map how our lead forms, CRM, and reports should connect...",
    "Build next week's campaign task plan...",
  ]);
  assert.equal(content.taskAnimationPause, "Pause examples");
  assert.equal(content.taskAnimationResume, "Resume examples");
  assert.equal(HOMEPAGE_TASK_TYPING_DELAY_MS, 27);
  assert.equal(HOMEPAGE_TASK_HOLD_MS, 900);
  assert.equal(content.taskLabel, "Your first task");
  assert.equal(content.taskSubmit, "Start");
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
      content.intro,
      content.title,
      content.lead,
      content.meetAssistants,
      content.taskPlaceholder,
      ...content.taskExamples,
      content.taskAnimationPause,
      content.taskAnimationResume,
      content.taskLabel,
      content.taskSubmit,
      content.taskStorageError,
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
    assert.equal(content.taskExamples.length, 3, `${locale} provides three task examples`);
    assert.equal(new Set(content.taskExamples).size, 3, `${locale} task examples are distinct`);
    assert.ok(content.taskPlaceholder.endsWith("..."), `${locale} task placeholder ends with an ellipsis`);
    assert.ok(content.taskExamples.every((example) => example.endsWith("...")), `${locale} task examples end with ellipses`);
    if (locale !== "en") {
      assert.notEqual(content.intro, english.intro, `${locale} localizes the product introduction`);
      assert.notEqual(content.title, english.title, `${locale} does not reuse the English headline`);
      assert.notEqual(content.lead, english.lead, `${locale} does not reuse the English lead`);
      assert.notEqual(content.taskPlaceholder, english.taskPlaceholder, `${locale} localizes the task prompt`);
      assert.notDeepEqual(content.taskExamples, english.taskExamples, `${locale} localizes the task examples`);
      assert.notEqual(content.taskAnimationPause, english.taskAnimationPause, `${locale} localizes the pause control`);
      assert.notEqual(content.taskAnimationResume, english.taskAnimationResume, `${locale} localizes the resume control`);
      assert.notEqual(content.developersBody, english.developersBody, `${locale} localizes the developer narrative`);
      assert.notEqual(content.usersBody, english.usersBody, `${locale} localizes the user narrative`);
    }
  }
});

test("preserves localized context order while emphasizing only Assistant identity data", () => {
  const challenge = {
    expires_in: 300,
    assistant: { name: "Example Assistant", version: "1.0.0" },
    action: { id: "review-action" },
  };
  for (const locale of LOCALES) {
    const parts = humanRequestContextParts(tr("human_context", locale), challenge);
    assert.equal(parts.map(({ text }) => text).join(""), tr("human_context", locale)
      .replace("{action}", challenge.action.id)
      .replace("{assistant}", challenge.assistant.name)
      .replace("{version}", challenge.assistant.version)
      .replace("{seconds}", String(challenge.expires_in)));
    assert.deepEqual(
      parts.filter(({ emphasized }) => emphasized).map(({ text }) => text),
      locale === "zh" || locale === "ja"
        ? [challenge.assistant.name, `v${challenge.assistant.version}`, challenge.action.id]
        : [challenge.action.id, challenge.assistant.name, `v${challenge.assistant.version}`],
    );
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
