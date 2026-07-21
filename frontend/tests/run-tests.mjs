import { spawnSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { availableParallelism } from "node:os";
import { join } from "node:path";

const workers = Math.max(1, Math.floor(availableParallelism() / 2));
const tests = readdirSync("tests")
  .filter((name) => name.endsWith(".test.js"))
  .sort()
  .map((name) => join("tests", name));

if (tests.length === 0) throw new Error("no Store Node tests found");

console.log(`Running ${tests.length} Store Node test files with ${workers} workers`);
const result = spawnSync(
  process.execPath,
  [
    "--test",
    `--test-concurrency=${workers}`,
    "--experimental-test-coverage",
    "--test-coverage-lines=99",
    "--test-coverage-branches=94",
    "--test-coverage-functions=94",
    ...tests,
  ],
  { stdio: "inherit" },
);

if (result.error) throw result.error;
process.exit(result.status ?? 1);
