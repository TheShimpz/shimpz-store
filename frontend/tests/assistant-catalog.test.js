// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { parseAssistantCatalog } from "../src/lib/assistantCatalog.js";

const DIGEST = `sha256:${"a".repeat(64)}`;
const ICON_DIGEST = `sha256:${"b".repeat(64)}`;

function catalog() {
  return {
    version: 1,
    assistants: [
      {
        assistant_id: "example-assistant",
        name: "Example Assistant",
        summary: "A safe example.",
        assistant_version: "1.2.3",
        creators: ["@creator"],
        github: "https://github.com/example/assistant",
        source_digest: DIGEST,
        icon_digest: ICON_DIGEST,
        platforms: ["linux/amd64", "linux/arm64"],
        allowed_hosts: ["api.example.com"],
        integrations: [{ id: "example", provider: "example", scopes: ["read"] }],
        actions: [{ id: "lookup", integrations: ["example"], human_requests: ["approval"] }],
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
    (value) => { value.assistants[0].actions = Array.from({ length: 65 }, () => structuredClone(value.assistants[0].actions[0])); },
    (value) => { value.assistants[0].actions[0].integrations = Array.from({ length: 17 }, (_, index) => `integration-${index}`); },
    (value) => { value.assistants[0].actions[0].integrations = ["a".repeat(65)]; },
    (value) => { value.assistants[0].integrations = "example"; },
    (value) => { value.assistants[0].actions = "lookup"; },
    (value) => { value.assistants[0].allowed_hosts = ["api.example.com", "api.example.com"]; },
    (value) => { value.assistants[0].allowed_hosts = [42]; },
    (value) => { value.assistants[0].allowed_hosts = Array.from({ length: 65 }, (_, index) => `api-${index}.example.com`); },
    (value) => { value.assistants[0].platforms = ["windows/amd64"]; },
    (value) => { value.assistants[0].integrations[0].scopes = ["read", "read"]; },
  ];
  for (const mutate of mutations) {
    const value = catalog();
    mutate(value);
    assert.throws(() => parseAssistantCatalog(value));
  }
});
