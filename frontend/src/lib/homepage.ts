import type { Locale } from "$lib/locales";

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  titleLines: readonly [string, string];
};

const SEO_TITLE = "Shimpz — Delegate Your Work to AI Assistants";

const CONTENT = {
  en: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordinates reviewed assistants on your computer, with the LLM you choose, so you can focus on what matters.",
    titleLines: ["I do the work so you can", "focus on what matters."],
  },
  pt: {
    seoTitle: SEO_TITLE,
    seoDescription: "O Shimpz coordena assistentes revisados no seu computador, com a LLM que você escolher, para que você se concentre no que importa.",
    titleLines: ["Eu faço o trabalho para que você", "possa focar no que importa."],
  },
  es: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordina asistentes revisados en tu ordenador, con el LLM que elijas, para que te centres en lo que importa.",
    titleLines: ["Hago el trabajo para que puedas", "enfocarte en lo que importa."],
  },
  fr: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordonne des assistants vérifiés sur votre ordinateur, avec le LLM de votre choix, pour vous laisser vous concentrer sur l’essentiel.",
    titleLines: ["Je fais le travail pour que vous", "vous concentriez sur l’essentiel."],
  },
  de: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz koordiniert geprüfte Assistants auf deinem Computer mit dem LLM deiner Wahl, damit du dich auf das Wesentliche konzentrieren kannst.",
    titleLines: ["Ich mache die Arbeit, damit du", "dich aufs Wesentliche konzentrierst."],
  },
  zh: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz 使用你选择的 LLM，在你的电脑上协调经过审核的 Assistant，让你专注于真正重要的事。",
    titleLines: ["我来完成工作，让你专注于", "真正重要的事。"],
  },
  ja: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz は選んだ LLM を使ってレビュー済みの Assistant をあなたのコンピューター上で連携させ、大切なことに集中できるようにします。",
    titleLines: ["仕事は私が引き受けます。", "あなたは大切なことに集中できます。"],
  },
  ar: {
    seoTitle: SEO_TITLE,
    seoDescription: "ينسّق Shimpz Assistants خضعت للمراجعة على حاسوبك باستخدام LLM الذي تختاره، لتتمكن من التركيز على ما يهم.",
    titleLines: ["أنجز العمل لتتمكن من", "التركيز على ما يهم."],
  },
} satisfies Record<Locale, HomepageContent>;

export function homepage(locale: Locale): HomepageContent {
  return CONTENT[locale];
}
