export const LOCALE_OPTIONS = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "pt", label: "Português", dir: "ltr" },
  { code: "es", label: "Español", dir: "ltr" },
  { code: "zh", label: "中文", dir: "ltr" },
  { code: "fr", label: "Français", dir: "ltr" },
  { code: "de", label: "Deutsch", dir: "ltr" },
  { code: "ja", label: "日本語", dir: "ltr" },
  { code: "ar", label: "العربية", dir: "rtl" },
] as const;

export type Locale = (typeof LOCALE_OPTIONS)[number]["code"];
export type Direction = (typeof LOCALE_OPTIONS)[number]["dir"];

export const LOCALES = LOCALE_OPTIONS.map(({ code }) => code) as Locale[];

export function isLocale(value: string): value is Locale {
  return LOCALES.includes(value as Locale);
}

export function localeDirection(locale: Locale): Direction {
  return LOCALE_OPTIONS.find(({ code }) => code === locale)?.dir ?? "ltr";
}
