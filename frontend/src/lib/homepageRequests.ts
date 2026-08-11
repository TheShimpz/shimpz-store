export type HomepageRequestGroup = "approval" | "input" | "auth";

export type HomepageRequest = {
  kind: string;
  call: string;
  signature: string;
  group: HomepageRequestGroup;
  image: string;
  height: number;
};

export const HOMEPAGE_REQUEST_ROTATION_MS = 3_000;

export const HOMEPAGE_REQUESTS = [
  { kind: "approval", call: "request_approval", signature: "request_approval(title=..., description=...)", group: "approval", image: "approval.png", height: 316 },
  { kind: "input:text", call: "request_input", signature: 'request_input(InputRequest(kind="text", ...))', group: "input", image: "input-text.png", height: 416 },
  { kind: "input:textarea", call: "request_input", signature: 'request_input(InputRequest(kind="textarea", ...))', group: "input", image: "input-textarea.png", height: 544 },
  { kind: "input:password", call: "request_input", signature: 'request_input(InputRequest(kind="password", ...))', group: "input", image: "input-password.png", height: 494 },
  { kind: "input:phone", call: "request_input", signature: 'request_input(InputRequest(kind="phone", ...))', group: "input", image: "input-phone.png", height: 416 },
  { kind: "input:select", call: "request_input", signature: 'request_input(InputRequest(kind="select", ...))', group: "input", image: "input-select.png", height: 416 },
  { kind: "input:choice", call: "request_input", signature: 'request_input(InputRequest(kind="choice", ...))', group: "input", image: "input-choice.png", height: 496 },
  { kind: "input:choices", call: "request_input", signature: 'request_input(InputRequest(kind="choices", ...))', group: "input", image: "input-choices.png", height: 486 },
  { kind: "auth:reauth", call: "request_auth", signature: 'request_auth("reauth", title=..., description=...)', group: "auth", image: "auth-reauth.png", height: 494 },
  { kind: "auth:second-factor", call: "request_auth", signature: 'request_auth("second-factor", title=..., description=...)', group: "auth", image: "auth-second-factor.png", height: 466 },
  { kind: "auth:phishing-resistant", call: "request_auth", signature: 'request_auth("phishing-resistant", title=..., description=...)', group: "auth", image: "auth-phishing-resistant.png", height: 378 },
] as const satisfies readonly HomepageRequest[];
