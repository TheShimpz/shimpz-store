// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { SERVICES, creatorOf, servicesByCreator, t } from "../src/lib/catalog.ts";

test("PostgreSQL is the only published Service", () => {
  assert.deepEqual(SERVICES.map((service) => service.id), ["postgres"]);
  assert.equal(t({ en: "Database", pt: "Banco" }, "pt"), "Banco");
  assert.equal(t({ en: "Database", pt: "Banco" }, "es"), "Database");
  assert.equal(creatorOf({}), "julianoamg");
  assert.deepEqual(servicesByCreator("julianoamg"), SERVICES);
});
