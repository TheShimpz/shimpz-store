export type HumanRequestContextPart = {
  text: string;
  emphasized: boolean;
};

export function humanRequestContextParts(
  template: string,
  challenge: Record<string, any>,
): HumanRequestContextPart[] {
  const replacements: Record<string, HumanRequestContextPart> = {
    "{action}": { text: challenge.action.id, emphasized: true },
    "{assistant}": { text: challenge.assistant.name, emphasized: true },
    "v{version}": { text: `v${challenge.assistant.version}`, emphasized: true },
    "{version}": { text: challenge.assistant.version, emphasized: true },
    "{seconds}": { text: String(challenge.expires_in), emphasized: false },
  };
  return template
    .split(/(\{action\}|\{assistant\}|v\{version\}|\{version\}|\{seconds\})/u)
    .filter(Boolean)
    .map((token) => replacements[token] ?? { text: token, emphasized: false });
}
