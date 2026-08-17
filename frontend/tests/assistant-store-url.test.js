// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import {
  closedAssistantStoreHref,
  requestedAssistantFromSearch,
} from "../src/lib/assistantStoreUrl.js";

test("uses only closed public Assistant Store destinations", () => {
  assert.equal(closedAssistantStoreHref("en", "shimpz-cloudflare"), "/en/assistants?assistant=shimpz-cloudflare");
  assert.equal(requestedAssistantFromSearch("?assistant=shimpz-cloudflare"), "shimpz-cloudflare");
  assert.equal(requestedAssistantFromSearch("?assistant=shimpz-cloudflare&install=true"), "");
  assert.equal(requestedAssistantFromSearch("?assistant=another-assistant"), "another-assistant");
  assert.equal(requestedAssistantFromSearch("?assistant=../unknown"), "");
  assert.equal(closedAssistantStoreHref("en", "another-assistant"), "/en/assistants?assistant=another-assistant");
  for (const locale of ["en", "pt", "es", "zh", "fr", "de", "ja", "ar"]) {
    assert.equal(
      closedAssistantStoreHref(locale, "shimpz-cloudflare"),
      `/${locale}/assistants?assistant=shimpz-cloudflare`,
    );
  }
  assert.throws(() => closedAssistantStoreHref("xx", "shimpz-cloudflare"));
  assert.throws(() => closedAssistantStoreHref("en", "../unknown"));
});
