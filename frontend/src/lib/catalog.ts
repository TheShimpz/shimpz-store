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
    summary: { en: "Provision one isolated database for each Hosted Team.", pt: "Provisiona um banco isolado para cada Time Hosted." },
    blurb: {
      en: "The Hosted Team lifecycle provisions one least-privilege Postgres database (proj_team_<id>) for Team-owned state. Assistants cannot declare or receive a PostgreSQL Service binding.",
      pt: "O lifecycle de Time Hosted provisiona um banco Postgres de menor privilégio (proj_team_<id>) para o estado do Time. Assistants não podem declarar nem receber binding do Service PostgreSQL.",
    },
    features: [
      { en: "A dedicated database (proj_team_<id>), provisioned with the Hosted Team", pt: "Um banco dedicado (proj_team_<id>), provisionado com o Time Hosted" },
      { en: "A least-privilege role scoped to that database only", pt: "Um papel de menor privilégio restrito só àquele banco" },
      { en: "A scoped connection for the Team — never an administrator credential", pt: "Uma conexão restrita ao Time — nunca uma credencial de administrador" },
      { en: "Isolation from every other Team database and from platform data", pt: "Isolamento de todos os outros bancos de Times e dos dados da plataforma" },
      { en: "Idempotent retirement and final removal with Team teardown", pt: "Aposentadoria idempotente e remoção final com o teardown do Time" },
    ],
    boundaries: [
      { en: "Available only to the Hosted Team lifecycle; no Assistant Service binding exists", pt: "Disponível apenas para o lifecycle de Time Hosted; não existe binding de Service para Assistant" },
      { en: "No platform or Postgres administrator credential enters a Team", pt: "Nenhuma credencial da plataforma ou de administrador Postgres entra em um Time" },
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
