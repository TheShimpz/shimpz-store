// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const privacy = readFileSync(new URL("../src/routes/privacy/+page.svelte", import.meta.url), "utf8");
const sitemap = readFileSync(new URL("../src/routes/sitemap.xml/+server.ts", import.meta.url), "utf8");

test("privacy policy covers protected platform and OAuth data", () => {
  assert.match(privacy, /Account information:/);
  assert.match(privacy, /OAuth access or refresh tokens/);
  assert.match(privacy, /AI model provider selected for that Team/);
  assert.match(privacy, /We do not sell personal information/);
  assert.match(privacy, /privacy@shimpz\.com/);
});

test("privacy policy has an exact public sitemap URL", () => {
  assert.match(sitemap, /paths\.push\("\/privacy"\)/);
});
