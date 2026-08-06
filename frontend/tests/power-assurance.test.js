// @ts-nocheck -- executed by Node's built-in test runner; browser globals are installed per test.
import assert from "node:assert/strict";
import test from "node:test";

import {
  createPowerAssuranceBody,
  decodeBase64url,
  encodeBase64url,
  parsePowerAssuranceHandle,
  parsePowerAssuranceOptions,
  serializePowerAssuranceCredential,
} from "../src/lib/powerAssurance.js";

function encoded(text) {
  return Buffer.from(text).toString("base64url");
}

test("projects the exact Account assurance handle", () => {
  assert.equal(
    parsePowerAssuranceHandle({ version: 1, handle: "a".repeat(43), expires_in: 120 }),
    "a".repeat(43),
  );
  for (const value of [
    null,
    { version: 1, handle: "short", expires_in: 120 },
    { version: 1, handle: "a".repeat(43), expires_in: 121 },
    { version: 1, handle: "a".repeat(43), expires_in: 120, token: "private" },
  ]) {
    assert.throws(() => parsePowerAssuranceHandle(value));
  }
});

test("binds factors only to one canonical Team challenge", () => {
  const challengeId = "b".repeat(32);
  assert.deepEqual(createPowerAssuranceBody("team_1", challengeId, "password", "secret"), {
    team_id: "team_1",
    challenge_id: challengeId,
    password: "secret",
  });
  assert.deepEqual(createPowerAssuranceBody("team_1", challengeId, null), {
    team_id: "team_1",
    challenge_id: challengeId,
  });
  for (const args of [
    ["bad-team", challengeId, "code", "123456"],
    ["team_1", "short", "code", "123456"],
    ["team_1", challengeId, "token", "private"],
  ]) {
    assert.throws(() => createPowerAssuranceBody(...args));
  }
});

test("converts only exact UV-required WebAuthn options", () => {
  const options = parsePowerAssuranceOptions({
    challenge: encoded("challenge"),
    timeout: 300_000,
    rpId: "shimpz.com",
    allowCredentials: [{ id: encoded("credential"), type: "public-key" }],
    userVerification: "required",
  });
  assert.equal(Buffer.from(options.challenge).toString(), "challenge");
  assert.equal(Buffer.from(options.allowCredentials[0].id).toString(), "credential");
  assert.equal(options.userVerification, "required");
  for (const value of [
    null,
    {
      challenge: encoded("challenge"),
      timeout: 300_001,
      rpId: "shimpz.com",
      allowCredentials: [{ id: encoded("credential"), type: "public-key" }],
      userVerification: "required",
    },
    {
      challenge: encoded("challenge"),
      timeout: 300_000,
      rpId: "shimpz.com",
      allowCredentials: [{ id: encoded("credential"), type: "password" }],
      userVerification: "required",
    },
  ]) {
    assert.throws(() => parsePowerAssuranceOptions(value));
  }
});

test("serializes one browser assertion without retaining browser objects", () => {
  const previousCredential = globalThis.PublicKeyCredential;
  const previousResponse = globalThis.AuthenticatorAssertionResponse;
  class AssertionResponse {}
  class Credential {}
  globalThis.PublicKeyCredential = Credential;
  globalThis.AuthenticatorAssertionResponse = AssertionResponse;
  try {
    const response = new AssertionResponse();
    response.clientDataJSON = Uint8Array.from([1, 2]).buffer;
    response.authenticatorData = Uint8Array.from([3, 4]).buffer;
    response.signature = Uint8Array.from([5, 6]).buffer;
    response.userHandle = Uint8Array.from([7]).buffer;
    const credential = new Credential();
    credential.id = "credential";
    credential.rawId = Uint8Array.from([8, 9]).buffer;
    credential.type = "public-key";
    credential.response = response;
    assert.deepEqual(serializePowerAssuranceCredential(credential), {
      id: "credential",
      rawId: "CAk",
      type: "public-key",
      response: {
        clientDataJSON: "AQI",
        authenticatorData: "AwQ",
        signature: "BQY",
        userHandle: "Bw",
      },
    });
    response.userHandle = null;
    assert.equal("userHandle" in serializePowerAssuranceCredential(credential).response, false);
    assert.throws(() => serializePowerAssuranceCredential({}));
  } finally {
    globalThis.PublicKeyCredential = previousCredential;
    globalThis.AuthenticatorAssertionResponse = previousResponse;
  }
});

test("round-trips bounded base64url buffers and rejects empty material", () => {
  const value = Uint8Array.from([0, 127, 128, 255]).buffer;
  assert.deepEqual(new Uint8Array(decodeBase64url(encodeBase64url(value))), new Uint8Array(value));
  assert.throws(() => decodeBase64url("not+padded"));
  assert.throws(() => encodeBase64url(new ArrayBuffer(0)));
});
