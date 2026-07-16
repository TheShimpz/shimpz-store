// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  ASSISTANT_INSTALL_ACK_TIMEOUT_MS,
  ASSISTANT_INSTALL_ACK_TYPE,
  ASSISTANT_STORE_CONTEXT_TYPE,
  ASSISTANT_STORE_FRAME_MAX_HEIGHT,
  ASSISTANT_STORE_FRAME_MIN_HEIGHT,
  ASSISTANT_STORE_FRAME_TYPE,
  acceptAssistantStoreContext,
  createAssistantStoreFrameMessage,
  createAssistantInstallRequest,
  classifyAssistantInstallAck,
  resolveInstallParentOrigin,
} from "../src/lib/assistantInstallBridge.js";

test("resolves only exact HTTP loopback Admin origins from the iframe referrer", () => {
  assert.equal(resolveInstallParentOrigin("http://127.0.0.1:7777/assistants/"), "http://127.0.0.1:7777");
  assert.equal(resolveInstallParentOrigin("http://localhost:7777/assistants/"), "http://localhost:7777");
  assert.equal(resolveInstallParentOrigin("http://[::1]:7777/assistants/"), "http://[::1]:7777");

  for (const referrer of [
    "",
    "https://127.0.0.1:7777/assistants/",
    "http://127.0.0.2:7777/assistants/",
    "http://localtest.me:7777/assistants/",
    "http://captain@localhost:7777/assistants/",
    "not a URL",
  ]) {
    assert.throws(() => resolveInstallParentOrigin(referrer));
  }
});

test("creates the exact inert Assistant install request", () => {
  assert.deepEqual(createAssistantInstallRequest("hello-pulse"), {
    type: "shimpz:assistant-install",
    version: 1,
    assistant: "hello-pulse",
  });
  for (const assistant of ["", "Hello-Pulse", "../hello", "hello_pulse", "a".repeat(81)]) {
    assert.throws(() => createAssistantInstallRequest(assistant));
  }
});

test("creates one exact bounded integer frame measurement", () => {
  assert.deepEqual(createAssistantStoreFrameMessage(719.2), {
    type: ASSISTANT_STORE_FRAME_TYPE,
    version: 1,
    height: 720,
  });
  assert.equal(createAssistantStoreFrameMessage(1).height, ASSISTANT_STORE_FRAME_MIN_HEIGHT);
  assert.equal(createAssistantStoreFrameMessage(9000).height, ASSISTANT_STORE_FRAME_MAX_HEIGHT);
  for (const height of [Number.NaN, Number.POSITIVE_INFINITY, "720", null]) {
    assert.throws(() => createAssistantStoreFrameMessage(height));
  }
});

test("accepts Store context only from the exact parent at an HTTP loopback origin", () => {
  const parentWindow = {};
  const data = { type: ASSISTANT_STORE_CONTEXT_TYPE, version: 1 };
  for (const origin of [
    "http://127.0.0.1:7777",
    "http://localhost:7777",
    "http://[::1]:7777",
  ]) {
    assert.equal(acceptAssistantStoreContext({ source: parentWindow, origin, data }, parentWindow), origin);
  }

  const rejected = [
    { source: {}, origin: "http://localhost:7777", data },
    { source: parentWindow, origin: "https://localhost:7777", data },
    { source: parentWindow, origin: "http://127.0.0.2:7777", data },
    { source: parentWindow, origin: "http://captain@localhost:7777", data },
    { source: parentWindow, origin: "http://localhost:7777/path", data },
    { source: parentWindow, origin: "http://localhost:7777", data: { ...data, extra: true } },
    { source: parentWindow, origin: "http://localhost:7777", data: { ...data, version: 2 } },
    { source: parentWindow, origin: "http://localhost:7777", data: { type: ASSISTANT_STORE_FRAME_TYPE, version: 1 } },
  ];
  for (const event of rejected) assert.equal(acceptAssistantStoreContext(event, parentWindow), null);
  assert.equal(acceptAssistantStoreContext(null, parentWindow), null);
  assert.equal(acceptAssistantStoreContext({ source: parentWindow, origin: "http://localhost", data }, null), null);
});

test("accepts only the exact generic ACK from the exact parent source and origin", () => {
  const parentWindow = {};
  const parentOrigin = "http://127.0.0.1:7777";
  const data = {
    type: ASSISTANT_INSTALL_ACK_TYPE,
    version: 1,
    assistant: "hello-pulse",
    accepted: true,
  };
  const context = { parentWindow, parentOrigin, assistant: "hello-pulse" };

  assert.equal(classifyAssistantInstallAck({ source: parentWindow, origin: parentOrigin, data }, context), "accepted");
  assert.equal(
    classifyAssistantInstallAck({ source: {}, origin: parentOrigin, data }, context),
    "ignore",
  );
  assert.equal(
    classifyAssistantInstallAck({ source: parentWindow, origin: "http://localhost:7777", data }, context),
    "ignore",
  );
  assert.equal(
    classifyAssistantInstallAck({ source: parentWindow, origin: parentOrigin, data: { type: "other" } }, context),
    "ignore",
  );
});

test("rejects every malformed trusted ACK and defines a bounded wait", () => {
  const parentWindow = {};
  const parentOrigin = "http://127.0.0.1:7777";
  const context = { parentWindow, parentOrigin, assistant: "hello-pulse" };
  const exact = {
    type: ASSISTANT_INSTALL_ACK_TYPE,
    version: 1,
    assistant: "hello-pulse",
    accepted: true,
  };
  const cases = [
    { ...exact, version: "1" },
    { ...exact, version: 2 },
    { ...exact, assistant: "salesnator" },
    { ...exact, accepted: false },
    { ...exact, capsule: "private_capsule" },
    { ...exact, token: "secret" },
  ];
  for (const data of cases) {
    assert.equal(classifyAssistantInstallAck({ source: parentWindow, origin: parentOrigin, data }, context), "invalid");
  }
  assert.equal(ASSISTANT_INSTALL_ACK_TIMEOUT_MS, 3000);
});
