// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { fetchAssistantCatalog, parseAssistantCatalog as parseLocalized } from "../src/lib/assistantCatalog.js";

const parseAssistantCatalog = (value) => parseLocalized(value, "en");

const DIGEST = `sha256:${"a".repeat(64)}`;
const ICON_DIGEST = `sha256:${"b".repeat(64)}`;

function catalog() {
  return {
    version: 1,
    locale: "en",
    assistants: [
      {
        assistant_id: "example-assistant",
        name: "Example Assistant",
        summary: "A safe example.",
        description: "Looks up example records and keeps every change behind explicit approval.",
        links: { site: "https://example.org/assistant", github: "https://github.com/example" },
        assistant_version: "1.2.3",
        creators: ["@creator"],
        github: "https://github.com/example/assistant",
        source_digest: DIGEST,
        icon_digest: ICON_DIGEST,
        platforms: ["linux/amd64", "linux/arm64"],
        allowed_hosts: ["api.example.com"],
        integrations: [{ id: "example", provider: "example", scopes: ["read"] }],
        stored_inputs: [{ id: "api-token", label: "API token" }],
        actions: [{
          id: "lookup",
          integrations: ["example"],
          human_requests: ["approval"],
          effect: "read_only",
          description: "Look up a record.",
        }],
      },
    ],
  };
}

test("projects the exact immutable publication identity needed by the Store", () => {
  assert.deepEqual(parseAssistantCatalog(catalog()), [
    {
      id: "example-assistant",
      name: "Example Assistant",
      summary: "A safe example.",
      version: "1.2.3",
      creators: ["@creator"],
      providers: ["example"],
      github: "https://github.com/example/assistant",
      platforms: ["linux/amd64", "linux/arm64"],
      allowedHosts: ["api.example.com"],
      integrations: [{ id: "example", provider: "example", scopes: ["read"] }],
      actions: [{ id: "lookup", integrations: ["example"], humanRequests: ["approval"] }],
      sourceDigest: DIGEST,
      iconDigest: ICON_DIGEST,
    },
  ]);
});

test("projects sorted unique Integration providers for public categorization", () => {
  const value = catalog();
  value.assistants[0].integrations = [
    { id: "zeta", provider: "zeta", scopes: ["read"] },
    { id: "alpha", provider: "alpha", scopes: ["read"] },
    { id: "alpha-write", provider: "alpha", scopes: ["write"] },
  ];
  assert.deepEqual(parseAssistantCatalog(value)[0].providers, ["alpha", "zeta"]);

  value.assistants[0].integrations = [];
  assert.deepEqual(parseAssistantCatalog(value)[0].providers, []);
});

test("fails closed on ambiguous or executable catalog data", () => {
  const mutations = [
    (value) => { value.extra = true; },
    (value) => { delete value.locale; },
    (value) => { value.locale = "pt"; },
    (value) => { value.version = 2; },
    (value) => { value.assistants[0].source_digest = "sha256:bad"; },
    (value) => { value.assistants[0].github = "javascript:alert(1)"; },
    (value) => { value.assistants[0].github = "https://example.com/assistant"; },
    (value) => { value.assistants[0].image_reference = "registry/image"; },
    (value) => { value.assistants.push(structuredClone(value.assistants[0])); },
    (value) => { value.assistants[0].actions[0].command = "/bin/sh"; },
    (value) => { delete value.assistants[0].actions[0].human_requests; },
    (value) => { value.assistants[0].actions[0].human_requests = ["input:magic"]; },
    (value) => { value.assistants[0].actions[0].human_requests = ["approval", "approval"]; },
    (value) => { value.assistants[0].actions = []; },
    (value) => { value.assistants[0].actions[0].integrations = Array.from({ length: 17 }, (_, index) => `integration-${index}`); },
    (value) => { value.assistants[0].actions[0].integrations = ["a".repeat(65)]; },
    (value) => { value.assistants[0].integrations = "example"; },
    (value) => { value.assistants[0].actions = "lookup"; },
    (value) => { value.assistants[0].allowed_hosts = ["api.example.com", "api.example.com"]; },
    (value) => { value.assistants[0].allowed_hosts = [42]; },
    (value) => { value.assistants[0].allowed_hosts = Array.from({ length: 65 }, (_, index) => `api-${index}.example.com`); },
    (value) => { value.assistants[0].platforms = ["windows/amd64"]; },
    (value) => { value.assistants[0].integrations[0].scopes = ["read", "read"]; },
    (value) => { delete value.assistants[0].description; },
    (value) => { value.assistants[0].description = ""; },
    (value) => { value.assistants[0].description = " Leading space."; },
    (value) => { value.assistants[0].description = "Line\nbreak."; },
    (value) => { value.assistants[0].description = "C1\u0085control."; },
    (value) => { value.assistants[0].description = "d".repeat(501); },
    (value) => { delete value.assistants[0].links; },
    (value) => { value.assistants[0].links = null; },
    (value) => { value.assistants[0].links = ["https://example.org/assistant"]; },
    (value) => { value.assistants[0].links.mastodon = "https://mastodon.social/@example"; },
    (value) => { value.assistants[0].links.constructor = "https://example.org/assistant"; },
    (value) => { value.assistants[0].links.github = "https://gitlab.com/example"; },
    (value) => { value.assistants[0].links.github = "https://github.com.evil.example/example"; },
    (value) => { value.assistants[0].links.x = "https://twitter.com/example"; },
    (value) => { value.assistants[0].links.youtube = "https://m.youtube.com/@example"; },
    (value) => { value.assistants[0].links.linkedin = "https://uk.linkedin.com/in/example"; },
    (value) => { value.assistants[0].links.instagram = "https://instagr.am/example"; },
    (value) => { value.assistants[0].links.site = "http://example.org/assistant"; },
    (value) => { value.assistants[0].links.site = "https://example.org"; },
    (value) => { value.assistants[0].links.site = "https://127.0.0.1/"; },
    (value) => { value.assistants[0].links.site = "https://intranet.local/"; },
    (value) => { value.assistants[0].links.site = "https://xn--80ak6aa92e.com/"; },
    (value) => { value.assistants[0].links.site = "https://example.org:8443/"; },
    (value) => { value.assistants[0].links.site = "https://user@example.org/"; },
    (value) => { value.assistants[0].links.site = "https://example.org/#top"; },
    (value) => { value.assistants[0].links.site = "https://example.org/a/../b"; },
    (value) => { value.assistants[0].links.site = `https://example.org/${"a".repeat(237)}`; },
    (value) => { value.assistants[0].links.site = 42; },
    (value) => { delete value.assistants[0].actions[0].effect; },
    (value) => { value.assistants[0].actions[0].effect = "destructive"; },
    (value) => { value.assistants[0].actions[0].effect = ["read_only"]; },
    (value) => { delete value.assistants[0].actions[0].description; },
    (value) => { value.assistants[0].actions[0].description = "a".repeat(121); },
    (value) => { value.assistants[0].actions[0].description = "Look up a record. "; },
    (value) => { value.assistants[0].actions[0].stored_inputs = ["api-token"]; },
    (value) => { delete value.assistants[0].stored_inputs; },
    (value) => { value.assistants[0].stored_inputs = "api-token"; },
    (value) => { value.assistants[0].stored_inputs = [42]; },
    (value) => { value.assistants[0].stored_inputs[0].label = "l".repeat(121); },
    (value) => { value.assistants[0].stored_inputs[0].label = ""; },
    (value) => { value.assistants[0].stored_inputs[0].id = "api.token"; },
    (value) => { value.assistants[0].stored_inputs[0].description = "Used to call the API."; },
    (value) => { value.assistants[0].stored_inputs.push({ id: "api-token", label: "Second" }); },
    (value) => {
      value.assistants[0].stored_inputs = Array.from({ length: 9 }, (_, index) => ({ id: `key-${index}`, label: "Key" }));
    },
  ];
  for (const mutate of mutations) {
    const value = catalog();
    mutate(value);
    assert.throws(() => parseAssistantCatalog(value));
  }
});

test("admits every Creator link kind on its host and the localized display copy up to its bounds", () => {
  const value = catalog();
  const entry = value.assistants[0];
  entry.links = {
    site: `https://example.org/${"a".repeat(236)}`,
    github: "https://github.com/example",
    x: "https://x.com/example",
    youtube: "https://www.youtube.com/@example",
    linkedin: "https://www.linkedin.com/company/example",
    instagram: "https://www.instagram.com/example",
  };
  entry.description = `${"d".repeat(499)}\u{1F44B}`;
  entry.actions[0] = { ...entry.actions[0], effect: "mutating", description: "\u00e1".repeat(120) };
  entry.stored_inputs = Array.from({ length: 8 }, (_, index) => ({ id: `key-${index}`, label: "\u00e7".repeat(120) }));
  assert.equal(parseAssistantCatalog(value).length, 1);

  entry.links = {
    youtube: "https://youtube.com/@example",
    linkedin: "https://linkedin.com/in/example",
    instagram: "https://instagram.com/example",
  };
  entry.stored_inputs = [];
  assert.equal(parseAssistantCatalog(value).length, 1);
  entry.links = {};
  assert.equal(parseAssistantCatalog(value).length, 1);
});

test("admits the producer's 128 Actions per Assistant and refuses one more", () => {
  const withActions = (count) => {
    const value = catalog();
    const action = value.assistants[0].actions[0];
    value.assistants[0].actions = Array.from({ length: count }, (_, index) => ({ ...action, id: `action-${index}` }));
    return value;
  };
  assert.equal(parseAssistantCatalog(withActions(128))[0].actions.length, 128);
  assert.throws(() => parseAssistantCatalog(withActions(129)));
});

test("admits exactly the producer's 1,000-entry catalog and refuses one more", () => {
  const entry = catalog().assistants[0];
  const entries = (count) => ({
    version: 1,
    locale: "en",
    assistants: Array.from({ length: count }, (_, index) => ({
      ...entry,
      assistant_id: `assistant-${String(index).padStart(4, "0")}`,
    })),
  });
  assert.equal(parseAssistantCatalog(entries(1000)).length, 1000);
  assert.throws(() => parseAssistantCatalog(entries(1001)), /too large/);
});

test("bounds the summary to 80 code points, a character outside the Basic Multilingual Plane counting once", () => {
  for (const summary of ["s".repeat(80), `${"s".repeat(79)}\u{1F44B}`]) {
    const value = catalog();
    value.assistants[0].summary = summary;
    assert.equal(parseLocalized(value, "en")[0].summary, summary);
  }
  const over = catalog();
  over.assistants[0].summary = "s".repeat(81);
  assert.throws(() => parseLocalized(over, "en"));
});

test("accepts only the catalog of exactly the requested interface language", () => {
  const value = catalog();
  value.locale = "pt";
  value.assistants[0].summary = "Um exemplo seguro.";
  assert.equal(parseLocalized(value, "pt")[0].summary, "Um exemplo seguro.");
  assert.throws(() => parseLocalized(value, "en"));
  assert.throws(() => parseLocalized(value, undefined));
});

test("fetches the catalog for one locale and refuses failures or a catalog in another locale", async () => {
  const requests = [];
  const fetcher = (body, ok = true, status = 200) => async (url, options) => {
    requests.push({ url, options });
    return { ok, status, json: async () => body };
  };
  const portuguese = { ...catalog(), locale: "pt" };
  assert.equal((await fetchAssistantCatalog(fetcher(portuguese), "pt")).length, 1);
  assert.deepEqual(requests[0], {
    url: "/api/assistants?locale=pt",
    options: { cache: "no-store", headers: { Accept: "application/json" } },
  });
  await assert.rejects(fetchAssistantCatalog(fetcher(portuguese), "ja"));
  await assert.rejects(fetchAssistantCatalog(fetcher({}, false, 503), "pt"), /HTTP 503/);
});
