// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  brainLoginEndpoints,
  parseBrainLoginChallenge,
  parseBrainLoginStatus,
} from "../src/lib/brainLogin.js";

test("Claude exposes an authorization URL before accepting a pasted code", () => {
  assert.deepEqual(
    parseBrainLoginChallenge("claude-code", {
      provider: "claude-code",
      mode: "authorization_code",
      url: "https://claude.ai/oauth/authorize?state=abc",
    }),
    { kind: "authorization_code", url: "https://claude.ai/oauth/authorize?state=abc" },
  );
});

test("Codex uses a device user code and never an imported auth.json payload", () => {
  assert.deepEqual(
    parseBrainLoginChallenge("codex", {
      url: "https://auth.openai.com/codex/device",
      user_code: "ABCD-EFGH",
    }),
    {
      kind: "device",
      url: "https://auth.openai.com/codex/device",
      userCode: "ABCD-EFGH",
    },
  );
  assert.equal(
    parseBrainLoginChallenge("codex", {
      url: "https://auth.openai.com/codex/device",
      auth_json: { tokens: "must-not-be-imported" },
    }),
    null,
  );
});

test("login challenges reject unsafe browser targets", () => {
  assert.equal(parseBrainLoginChallenge("claude-code", { url: "http://claude.ai/oauth" }), null);
  assert.equal(parseBrainLoginChallenge("claude-code", { url: "https://user:secret@claude.ai/oauth" }), null);
  assert.equal(parseBrainLoginChallenge("claude-code", { url: "javascript:alert(1)" }), null);
  assert.equal(parseBrainLoginChallenge("claude-code", { url: "https://evil.example/oauth/authorize" }), null);
  assert.equal(parseBrainLoginChallenge("claude-code", { url: "https://claude.ai/account" }), null);
  assert.equal(
    parseBrainLoginChallenge("claude-code", {
      provider: "codex",
      mode: "device_code",
      url: "https://claude.ai/oauth/authorize",
    }),
    null,
  );
  assert.equal(
    parseBrainLoginChallenge("codex", {
      url: "https://auth.openai.com.evil.example/codex/device",
      user_code: "ABCD-EFGH",
    }),
    null,
  );
  assert.equal(
    parseBrainLoginChallenge("codex", {
      url: "https://auth.openai.com/codex/device",
      user_code: "abcd-efgh",
    }),
    null,
  );
  assert.equal(
    parseBrainLoginChallenge("codex", {
      url: "https://auth.openai.com/codex/device?next=evil",
      user_code: "ABCD-EFGH",
    }),
    null,
  );
});

test("Capsule login routes are fixed and Capsule identifiers are validated", () => {
  assert.deepEqual(brainLoginEndpoints("account_capsule-1"), {
    start: "/api/capsules/account_capsule-1/brain/login/start",
    challenge: "/api/capsules/account_capsule-1/brain/login/url",
    code: "/api/capsules/account_capsule-1/brain/login/code",
    status: "/api/capsules/account_capsule-1/brain/login/status",
    cancel: "/api/capsules/account_capsule-1/brain/login/cancel",
  });
  assert.throws(() => brainLoginEndpoints("../another-capsule"), /Invalid Capsule/);
});

test("login status exposes only bounded, known state", () => {
  assert.deepEqual(parseBrainLoginStatus({ loggedIn: true, state: "succeeded" }), {
    loggedIn: true,
    lastError: "",
    state: "succeeded",
  });
  assert.deepEqual(parseBrainLoginStatus({ loggedIn: false, last_error: "x".repeat(500), state: "hostile" }), {
    loggedIn: false,
    lastError: "x".repeat(300),
    state: "",
  });
});
