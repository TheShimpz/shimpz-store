// @ts-nocheck -- executed by Node's built-in test runner; the browser bundle has no Node typings.
import assert from "node:assert/strict";
import test from "node:test";

import { ASSISTANT_BY_ID, SERVICE_BY_ID } from "../src/lib/catalog.ts";

test("Shimpz Assistant exposes its canonical Account and Secret contract", () => {
  const assistant = ASSISTANT_BY_ID.get("shimpz-assistant");

  assert.ok(assistant);
  assert.equal(assistant.version, "0.6.0");
  assert.deepEqual(
    assistant.powers.map((power) => power.id),
    [
      "public-user-lookup",
      "identity-me",
      "create-post",
      "delete-post",
      "list-direct-uploads",
      "create-test-direct-upload",
      "cancel-direct-upload",
      "verify-mux-webhook",
    ],
  );
  assert.match(assistant.summary.en, /X Accounts/);
  assert.match(assistant.summary.en, /Mux BYOK Secrets/);
  assert.match(assistant.description.en, /api\.x\.com/);
  assert.match(assistant.description.en, /api\.mux\.com/);
  assert.match(assistant.description.en, /without network access/);
  assert.deepEqual(assistant.permissions, [
    {
      en: "Allowed hosts: api.x.com and api.mux.com only",
      pt: "Hosts permitidos: somente api.x.com e api.mux.com",
    },
    {
      en: "Account: controller-owned X OAuth 2.0 with S256 PKCE; its token reaches only the declared X Power invocation",
      pt: "Account: OAuth 2.0 do X com S256 PKCE sob custódia do controller; seu token chega somente à execução do Power do X declarado",
    },
    {
      en: "Secrets: Mux Token ID, Token Secret and Webhook Signing Secret are requested just in time and injected only into the declaring Power",
      pt: "Secrets: Token ID, Token Secret e Webhook Signing Secret do Mux são solicitados sob demanda e injetados somente no Power que os declara",
    },
    {
      en: "Approval: required for every Post create/delete and Mux upload create/cancel invocation",
      pt: "Aprovação: obrigatória para cada criação/exclusão de Post e criação/cancelamento de upload do Mux",
    },
  ]);
});

test("OpenAI media Service publishes only its implemented operations", () => {
  const service = SERVICE_BY_ID.get("openai");

  assert.ok(service);
  assert.deepEqual(service.summary, {
    en: "Audited image, transcription, and speech operations.",
    pt: "Operações auditadas de imagem, transcrição e voz.",
  });
  assert.deepEqual(service.blurb, {
    en: "The audited OpenAI media sidecar implements allow-listed image generation, speech-to-text transcription, and text-to-speech. These operations are not yet exposed through an Assistant Power.",
    pt: "O sidecar auditado de mídia OpenAI implementa geração de imagens, transcrição de voz em texto e conversão de texto em voz permitidas. Essas operações ainda não são expostas por um Power de Assistant.",
  });
  assert.deepEqual(service.features, [
    { en: "Image generation (gpt-image)", pt: "Geração de imagens (gpt-image)" },
    { en: "Speech-to-text transcription", pt: "Transcrição de fala para texto" },
    { en: "Text-to-speech voice", pt: "Voz de texto para fala" },
  ]);
  assert.deepEqual(service.boundaries, [
    {
      en: "Every request is audited; the media API key remains inside the sidecar",
      pt: "Toda requisição é auditada; a chave de API de mídia permanece dentro do sidecar",
    },
    {
      en: "No Assistant Power or Assistant route exposes these operations yet",
      pt: "Nenhum Power nem rota de Assistant expõe essas operações ainda",
    },
    {
      en: "Only allow-listed image, transcription and speech operations are accepted",
      pt: "Somente operações permitidas de imagem, transcrição e fala são aceitas",
    },
  ]);
});
