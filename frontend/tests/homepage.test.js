// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { formatCatalogCount, homepage } from "../src/lib/homepage.ts";
import {
  HOMEPAGE_REQUESTS,
  homepageRequestChallenge,
  homepageRequestLabel,
} from "../src/lib/homepageRequests.ts";
import { LOCALES } from "../src/lib/locales.ts";

test("freezes the exact first-person English homepage narrative", () => {
  const content = homepage("en");
  assert.equal(content.title, "Give me a goal and my assistants do the work on your computer");
  assert.equal(content.lead, "No agents. No code. Just a team. Assistants that already work — with the LLM you choose.");
  assert.equal(content.watchMeWork, "See how I ask");
  assert.deepEqual(content.humanRequests, {
    heading: "I ask before I act.",
    body: "When an Assistant needs your decision, a missing value, or fresh authentication, I pause its Power and ask you directly. Every request is bound to that exact Assistant, Power, and action.",
    sdkSummary: "My SDK gives Creators three calls and 11 closed request kinds. Assistants cannot invent forms or authentication ceremonies at runtime.",
    sdkCta: "Explore my SDK on GitHub",
    menuLabel: "Power human request kinds",
    interfaceLabel: "Real interface",
    groupNotes: {
      approval: "I record your decision for one described action. Approval is attributable, one-use, and bound to the exact request.",
      input: "I render one closed, bounded field. input:password is only for a third-party secret deliberately delivered to the named Assistant — never your Shimpz password.",
      auth: "I run the trusted authentication ceremony. Passwords, authenticator codes, and passkey evidence never enter Assistant code.",
    },
  });
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
      content.humanRequests.heading,
      content.humanRequests.body,
      content.humanRequests.sdkSummary,
      content.humanRequests.sdkCta,
      content.humanRequests.menuLabel,
      content.humanRequests.interfaceLabel,
      ...Object.values(content.humanRequests.groupNotes),
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
      assert.notEqual(content.humanRequests.body, english.humanRequests.body, `${locale} localizes the Power request narrative`);
      assert.notEqual(content.developersBody, english.developersBody, `${locale} localizes the developer narrative`);
      assert.notEqual(content.usersBody, english.usersBody, `${locale} localizes the user narrative`);
    }
  }
});

test("keeps every closed Power request kind renderable as localized interface data", () => {
  assert.deepEqual(HOMEPAGE_REQUESTS.map(({ kind }) => kind), [
    "approval",
    "input:text",
    "input:textarea",
    "input:password",
    "input:phone",
    "input:select",
    "input:choice",
    "input:choices",
    "auth:reauth",
    "auth:second-factor",
    "auth:phishing-resistant",
  ]);

  for (const locale of LOCALES) {
    for (const request of HOMEPAGE_REQUESTS) {
      const label = homepageRequestLabel(request, locale);
      const challenge = homepageRequestChallenge(request, locale);
      assert.ok(label.trim().length > 0, `${locale} ${request.kind} has a human-readable label`);
      if (locale !== "en") {
        assert.notEqual(label, homepageRequestLabel(request, "en"), `${locale} ${request.kind} has a native label`);
      }
      assert.equal(challenge.request.kind, request.kind);
      assert.equal(challenge.request.title, label);
      assert.ok(challenge.request.label.trim().length > 0);
      assert.notEqual(challenge.request.label, challenge.request.title);
      assert.ok(challenge.request.description.trim().length > 0);
      assert.ok(challenge.power.summary.trim().length > 0);
      assert.equal("image" in request, false, `${request.kind} is rendered instead of screenshotted`);
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
