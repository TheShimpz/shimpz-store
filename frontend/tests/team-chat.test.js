// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  CHAT_WS_SUBPROTOCOL,
  createHumanResponse,
  createTeamChatTurn,
  parseChatEvent,
  parseTeamChatAssistantScope,
  parseTeamStorage,
  parseTeamUpload,
  parseChatTerminalEvent,
  teamChatReconnectDelay,
  teamChatWebSocketPath,
} from "../src/lib/teamChat.js";

function humanRequest(kind, fields = {}) {
  return {
    kind,
    ordinal: 0,
    title: "Provide reviewed input",
    description: "Provide only the information requested by this exact Action.",
    fingerprint: "d".repeat(64),
    ...fields,
  };
}

function humanChallenge(request = humanRequest("approval")) {
  return {
    type: "human-required",
    challenge_id: "c".repeat(32),
    expires_in: 300,
    assistant: { id: "shimpz-cloudflare", name: "Shimpz Cloudflare", version: "0.4.1" },
    action: { id: "list-zones", summary: "List reviewed Cloudflare zones." },
    request,
  };
}

const file = {
  id: "a".repeat(32),
  name: "brief.txt",
  media_type: "text/plain",
  size: 5,
  sha256: "b".repeat(64),
};
const usage = { used_bytes: 5, limit_bytes: 100 * 1024 * 1024, remaining_bytes: 100 * 1024 * 1024 - 5 };

test("creates a strict Team-scoped chat turn with an explicit Assistant scope", () => {
  assert.deepEqual(createTeamChatTurn("  hello  ", [file.id], ["shimpz-cloudflare"]), {
    message: "hello",
    files: [file.id],
    assistant_ids: ["shimpz-cloudflare"],
  });
  assert.deepEqual(createTeamChatTurn("brain only"), {
    message: "brain only",
    files: [],
    assistant_ids: [],
  });
  for (const message of ["", { provider: "openai" }]) {
    assert.throws(() => createTeamChatTurn(message));
  }
  for (const files of [
    ["../escape"],
    [file.id, file.id],
    Array.from({ length: 9 }, (_, index) => index.toString(16).padStart(32, "0")),
  ]) {
    assert.throws(() => createTeamChatTurn("hello", files));
  }
  for (const assistants of [
    ["../escape"],
    ["shimpz-cloudflare", "shimpz-cloudflare"],
    Array.from({ length: 17 }, (_, index) => `assistant-${index}`),
  ]) {
    assert.throws(() => createTeamChatTurn("hello", [], assistants));
  }
});

test("accepts only an exact bounded default Assistant scope", () => {
  assert.deepEqual(
    parseTeamChatAssistantScope({ assistant_ids: ["shimpz-cloudflare"] }),
    ["shimpz-cloudflare"],
  );
  assert.deepEqual(parseTeamChatAssistantScope({ assistant_ids: [] }), []);
  for (const inventory of [
    null,
    { installed: ["shimpz-cloudflare"] },
    { assistant_ids: ["shimpz-cloudflare"], private: true },
    { assistant_ids: ["bad_id"] },
    { assistant_ids: ["shimpz-cloudflare", "shimpz-cloudflare"] },
  ]) {
    assert.throws(() => parseTeamChatAssistantScope(inventory));
  }
});

test("accepts only exact bounded terminal events from the authoritative Team", () => {
  const terminalEvents = [
    { type: "done", team_id: "marketing", team_name: "Marketing", reply: "complete" },
    { type: "error", status: 504, detail: "provider timed out" },
    { type: "stopped" },
  ];
  for (const event of terminalEvents) {
    assert.deepEqual(parseChatTerminalEvent(event, "marketing", "Marketing"), event);
  }

  for (const event of [
    { type: "text", text: "partial" },
    { type: "tool", label: "shell" },
    { type: "ask", text: "approve?" },
    { type: "answered", answered: true },
    { type: "done", team_id: "marketing", team_name: "Marketing", reply: "complete", trace: [] },
    { type: "done", team_id: "sales", team_name: "Marketing", reply: "complete" },
    { type: "done", team_id: "marketing", team_name: "Sales", reply: "complete" },
    { type: "done", team_id: "marketing", team_name: " Marketing ", reply: "complete" },
    { type: "done", team_id: "marketing", team_name: "Marketing", reply: "x".repeat(60_001) },
    { type: "done", team_name: "Marketing", reply: "complete" },
    { type: "error", status: true, detail: "failed" },
    { type: "error", status: 200, detail: "not an error" },
    { type: "error", status: 502, detail: "x".repeat(801) },
    { type: "stopped", requested: true },
  ]) {
    assert.throws(() => parseChatTerminalEvent(event, "marketing", "Marketing"));
  }
});

test("uses the single versioned Team chat WebSocket contract", () => {
  assert.equal(CHAT_WS_SUBPROTOCOL, "shimpz.chat.v4");
  assert.equal(teamChatWebSocketPath("team_one"), "/api/teams/team_one/chat/ws");
  for (const teamId of ["", "../escape", "team-one", "A"]) {
    assert.throws(() => teamChatWebSocketPath(teamId));
  }
});

test("uses the terminal event contract for browser chat", () => {
  assert.deepEqual(
    parseChatEvent(
      { type: "done", team_id: "marketing", team_name: "Marketing", reply: "complete" },
      "marketing",
      "Marketing",
    ),
    { type: "done", team_id: "marketing", team_name: "Marketing", reply: "complete" },
  );
  for (const retired of [
    { type: "input-required" },
    { type: "approval-required" },
  ]) {
    assert.throws(() => parseChatEvent(retired, "marketing", "Marketing"));
  }
});

test("accepts all and only the eleven reviewed Action human request descriptors", () => {
  const options = [
    { value: "one", label: "One", description: null },
    { value: "two", label: "Two", description: "Second option" },
  ];
  const descriptors = [
    humanRequest("approval"),
    humanRequest("auth:password"),
    humanRequest("auth:totp"),
    humanRequest("auth:passkey"),
    ...[
      ["input:text", 4_096],
      ["input:textarea", 16_000],
      ["input:password", 1_024],
      ["input:phone", 64],
    ].map(([kind, maximum]) => humanRequest(kind, {
      label: "Requested value",
      required: true,
      placeholder: null,
      min_length: 1,
      max_length: maximum,
    })),
    humanRequest("input:select", { label: "Select", required: true, options }),
    humanRequest("input:choice", { label: "Choose", required: true, options }),
    humanRequest("input:choices", {
      label: "Choose several",
      required: true,
      options,
      min_selections: 1,
      max_selections: 2,
    }),
  ];

  for (const descriptor of descriptors) {
    assert.deepEqual(
      parseChatEvent(humanChallenge(descriptor), "marketing", "Marketing"),
      humanChallenge(descriptor),
    );
  }
  for (const invalid of [
    { ...humanChallenge(), private: "must-not-cross" },
    humanChallenge({ ...humanRequest("approval"), secret: "must-not-cross" }),
    humanChallenge(humanRequest("unreviewed")),
    { ...humanChallenge(), challenge_id: "short" },
    { ...humanChallenge(), expires_in: 301 },
    { ...humanChallenge(), assistant: null },
    { ...humanChallenge(), assistant: { id: "bad_id", name: "Bad" } },
    humanChallenge({ ...humanRequest("approval"), ordinal: 8 }),
    humanChallenge({ ...humanRequest("approval"), fingerprint: "short" }),
    humanChallenge({ ...humanRequest("approval"), title: " spaced " }),
    humanChallenge(humanRequest("input:text", {
      label: "Text",
      required: true,
      placeholder: null,
      min_length: 0,
      max_length: 4_097,
    })),
    humanChallenge(humanRequest("input:select", {
      label: "Select",
      required: true,
      options: [{ value: "one", label: "One", description: null }],
    })),
    humanChallenge(humanRequest("input:select", {
      label: "Select",
      required: true,
      options: [
        { value: "one", label: "One", description: null },
        { value: "one", label: "Duplicate", description: null },
      ],
    })),
    humanChallenge(humanRequest("input:choice", {
      label: "Choice",
      required: true,
      options: [
        { value: "one", label: "One", description: null },
        { value: "two", label: "Two" },
      ],
    })),
    humanChallenge(humanRequest("input:choices", {
      label: "Choices",
      required: true,
      options,
      min_selections: 2,
      max_selections: 1,
    })),
  ]) {
    assert.throws(() => parseChatEvent(invalid, "marketing", "Marketing"));
  }
});

test("creates only exact challenge-bound human response frames", () => {
  const challengeId = "a".repeat(32);
  assert.deepEqual(createHumanResponse(challengeId, "deny"), {
    type: "human-response",
    challenge_id: challengeId,
    decision: "deny",
  });
  assert.deepEqual(createHumanResponse(challengeId, "submit", "value"), {
    type: "human-response",
    challenge_id: challengeId,
    decision: "submit",
    value: "value",
  });
  assert.deepEqual(createHumanResponse(challengeId, "submit", ["one", "two"]), {
    type: "human-response",
    challenge_id: challengeId,
    decision: "submit",
    value: ["one", "two"],
  });
  for (const [id, decision, value] of [
    ["short", "submit", true],
    [challengeId, "submit", false],
    [challengeId, "submit", ["one", "one"]],
    [challengeId, "skip", true],
  ]) {
    assert.throws(() => createHumanResponse(id, decision, value));
  }
});

test("caps Team chat reconnect backoff without encoding automatic replay", () => {
  assert.deepEqual(
    [0, 1, 2, 3, 4, 20].map(teamChatReconnectDelay),
    [400, 800, 1600, 3200, 5000, 5000],
  );
  for (const invalid of [-1, 0.5, "1", null]) {
    assert.throws(() => teamChatReconnectDelay(invalid));
  }
});

test("keeps Team files opaque and drops every path-like upstream field", () => {
  const inventory = parseTeamStorage({
    files: [{ ...file, created_at: 1_700_000_000, path: "/private/blob" }],
    ...usage,
    mount: "/private",
  });
  const uploaded = parseTeamUpload({
    file: { ...file, created_at: 1_700_000_000, path: "/private/blob" },
    ...usage,
  });

  assert.deepEqual(inventory, { files: [{ ...file, created_at: 1_700_000_000 }], ...usage });
  assert.deepEqual(uploaded, { file: { ...file, created_at: 1_700_000_000 }, ...usage });
  assert.deepEqual(
    parseTeamStorage({ files: [], used_bytes: 8, limit_bytes: 4, remaining_bytes: 0 }),
    { files: [], used_bytes: 8, limit_bytes: 4, remaining_bytes: 0 },
  );
  assert.equal("path" in inventory.files[0], false);
  assert.equal("path" in uploaded.file, false);
  assert.throws(() => parseTeamUpload({ file, ...usage }));
  assert.throws(() => parseTeamUpload({ file: { ...file, size: 0, created_at: 1 }, ...usage }));
  assert.throws(() => parseTeamUpload({ file: { ...file, size: 25 * 1024 * 1024 + 1, created_at: 1 }, ...usage }));
});

test("rejects forged, duplicate and inconsistent Team inventories", () => {
  for (const value of [
    null,
    { files: "many", ...usage },
    { files: [{ ...file, id: "../escape", created_at: 1 }], ...usage },
    { files: [{ ...file, name: "../brief.txt", created_at: 1 }], ...usage },
    { files: [{ ...file, created_at: 1 }, { ...file, created_at: 2 }], ...usage },
    { files: [{ ...file, created_at: 1 }], ...usage, remaining_bytes: 0 },
  ]) {
    assert.throws(() => parseTeamStorage(value));
  }
});
