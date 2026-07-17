const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;

export const MODEL_PROVIDERS = Object.freeze([
  Object.freeze({ id: "openai", title: "OpenAI", defaultModel: "gpt-5.5" }),
  Object.freeze({ id: "anthropic", title: "Anthropic", defaultModel: "claude-sonnet-5" }),
]);

/** @param {unknown} value */
export function modelProvider(value) {
  if (typeof value !== "string") return null;
  const id = value.trim().toLowerCase();
  return MODEL_PROVIDERS.find((provider) => provider.id === id) ?? null;
}

/** @param {unknown} value */
export function defaultModelFor(value) {
  return modelProvider(value)?.defaultModel ?? "";
}

/** @param {unknown} provider @param {unknown} model */
export function normalizeInferenceSelection(provider, model) {
  const definition = modelProvider(provider);
  if (!definition) throw new TypeError("Unsupported model provider");
  const selectedModel = String(model || definition.defaultModel).trim();
  if (!MODEL_ID.test(selectedModel)) throw new TypeError("Invalid model identifier");
  return { provider: definition.id, model: selectedModel };
}
