// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_PENDING_TASK_CHARS,
  PENDING_TASK_KEY,
  savePendingTask,
  takePendingTask,
} from "../src/lib/pendingTask.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
    values,
  };
}

test("stores one bounded trimmed homepage task", () => {
  const storage = memoryStorage();
  assert.equal(savePendingTask(storage, "  Review my DNS records  "), true);
  assert.equal(storage.getItem(PENDING_TASK_KEY), "Review my DNS records");
  assert.equal(savePendingTask(storage, "   "), false);
  assert.equal(savePendingTask(storage, "x".repeat(MAX_PENDING_TASK_CHARS + 1)), false);
});

test("takes the pending task once and rejects invalid stored values", () => {
  const storage = memoryStorage({ [PENDING_TASK_KEY]: "  Review my DNS records  " });
  assert.equal(takePendingTask(storage), "Review my DNS records");
  assert.equal(takePendingTask(storage), "");

  const oversized = memoryStorage({ [PENDING_TASK_KEY]: "x".repeat(MAX_PENDING_TASK_CHARS + 1) });
  assert.equal(takePendingTask(oversized), "");
  assert.equal(oversized.getItem(PENDING_TASK_KEY), null);
});
