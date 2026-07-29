// The Shimpz capability catalog is the source of truth for public Service documentation.

export const LOCALES = ["en", "pt"] as const;
export type Locale = (typeof LOCALES)[number];
export type I18n = Record<Locale, string>;
export const t = (v: I18n, l: Locale): string => v[l] ?? v.en;

// ── Services (audited platform capability inventory) ────────────────────────────────────────────
type ServiceCategory = "Data" | "Network" | "Dev" | "Automation";

export type ServiceIconName = "database";

export interface Service {
  id: string;
  name: string; // brand/technical name — not translated
  category: ServiceCategory;
  icon: ServiceIconName; // semantic Shimpz glyph; rendered as a code-native SVG
  brand?: string; // official BRAND COLOR (recognition) for third-party Services — not a reproduced logo
  summary: I18n; // one line, human-readable
  blurb: I18n; // a paragraph
  features: I18n[]; // the COMPLETE list of shipping operations for this platform component
  boundaries: I18n[]; // who can call it and the limits of that access; never an implied Assistant grant
  creator?: string; // Creator handle — defaults to the platform owner (see DEFAULT_CREATOR)
}

export const SERVICES: Service[] = [
  {
    id: "postgres", name: "Postgres", category: "Data", icon: "database", brand: "#336791",
    summary: { en: "Provision an isolated database for one admitted workload.", pt: "Provisiona um banco isolado para um workload admitido." },
    blurb: {
      en: "The current internal lifecycle can provision one least-privilege Postgres database (proj_<name>) per admitted workload. Assistant Spec v1 can request the Service operation, but the generic runtime binding is not released yet.",
      pt: "O lifecycle interno atual pode provisionar um banco Postgres de menor privilégio (proj_<name>) por workload admitido. A Assistant Spec v1 pode solicitar a operação do Service, mas o binding genérico de runtime ainda não foi lançado.",
    },
    features: [
      { en: "A dedicated database (proj_<name>), provisioned on install", pt: "Um banco dedicado (proj_<name>), provisionado na instalação" },
      { en: "A least-privilege role scoped to that database only", pt: "Um papel de menor privilégio restrito só àquele banco" },
      { en: "Full read/write, schema and migrations within its own database", pt: "Leitura/escrita completa, schema e migrações no próprio banco" },
      { en: "A scoped connection for the admitted workload — never an administrator credential", pt: "Uma conexão restrita ao workload admitido — nunca uma credencial de administrador" },
      { en: "Fully isolated from another workload's data and from platform data", pt: "Totalmente isolado dos dados de outro workload e dos dados da plataforma" },
      { en: "Dropped cleanly on uninstall", pt: "Removido de forma limpa ao desinstalar" },
    ],
    boundaries: [
      { en: "Available through the current internal App lifecycle; Assistant binding is not released", pt: "Disponível pelo lifecycle interno atual de Apps; o binding para Assistant não foi lançado" },
      { en: "No platform or Postgres administrator credential enters a tenant workload", pt: "Nenhuma credencial da plataforma ou de administrador Postgres entra em um workload do tenant" },
    ],
  },
];

export const SERVICE_BY_ID = new Map(SERVICES.map((service) => [service.id, service]));

// ── Creators ─────────────────────────────────────────────────────────────────────────
// A Creator owns platform artifacts such as Services. GitHub identity is explicit catalog metadata;
// the handle is the profile slug. Platform-owned artifacts default to DEFAULT_CREATOR.
export const DEFAULT_CREATOR = "julianoamg";
export const creatorOf = (x: { creator?: string }): string => x.creator ?? DEFAULT_CREATOR;

export interface Creator {
  handle: string; // GitHub handle — also the profile slug
  name: string;
  github: string; // explicit github.com/<github> profile metadata; unrelated to account signup
  bio: I18n;
}

export const CREATORS: Creator[] = [
  {
    handle: "julianoamg",
    name: "Juliano Amaral Gouveia",
    github: "julianoamg",
    bio: {
      en: "Creator of Shimpz and its default audited platform Services.",
      pt: "Criador do Shimpz e de seus Services de plataforma auditados padrão.",
    },
  },
];

export const CREATOR_BY_HANDLE = new Map(CREATORS.map((c) => [c.handle, c]));
export const servicesByCreator = (handle: string): Service[] => SERVICES.filter((service) => creatorOf(service) === handle);
