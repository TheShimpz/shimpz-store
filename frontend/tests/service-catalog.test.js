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

test("PostgreSQL is exposed only as Hosted Team infrastructure", () => {
  const [postgresql] = SERVICES;
  assert.match(postgresql.summary.en, /Hosted Team/);
  assert.match(postgresql.boundaries[0].en, /no Assistant Service binding exists/);
  assert.doesNotMatch(JSON.stringify(postgresql), /App lifecycle|admitted workload|request the Service/);
});
