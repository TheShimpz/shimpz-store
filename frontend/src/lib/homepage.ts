import type { Locale } from "$lib/locales";

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  title: {
    accent: string;
    remainder: string;
    secondLine: string;
  };
};

const SEO_TITLE = "Shimpz — Delegate Your Work to AI Assistants";

const CONTENT = {
  en: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordinates reviewed assistants on your computer, with the LLM you choose, so you can focus on what matters.",
    title: { accent: "I do the work", remainder: "so you can", secondLine: "focus on what matters." },
  },
  pt: {
    seoTitle: SEO_TITLE,
    seoDescription: "O Shimpz coordena assistentes revisados no seu computador, com a LLM que você escolher, para que você se concentre no que importa.",
    title: { accent: "Eu faço o trabalho", remainder: "para que você", secondLine: "possa focar no que importa." },
  },
  es: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordina asistentes revisados en tu ordenador, con el LLM que elijas, para que te centres en lo que importa.",
    title: { accent: "Hago el trabajo", remainder: "para que puedas", secondLine: "enfocarte en lo que importa." },
  },
  fr: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz coordonne des assistants vérifiés sur votre ordinateur, avec le LLM de votre choix, pour vous laisser vous concentrer sur l’essentiel.",
    title: { accent: "Je fais le travail", remainder: "pour que vous", secondLine: "vous concentriez sur l’essentiel." },
  },
  de: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz koordiniert geprüfte Assistants auf deinem Computer mit dem LLM deiner Wahl, damit du dich auf das Wesentliche konzentrieren kannst.",
    title: { accent: "Ich mache die Arbeit,", remainder: "damit du", secondLine: "dich aufs Wesentliche konzentrierst." },
  },
  zh: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz 使用你选择的 LLM，在你的电脑上协调经过审核的 Assistant，让你专注于真正重要的事。",
    title: { accent: "我来完成工作", remainder: "，让你专注于", secondLine: "真正重要的事。" },
  },
  ja: {
    seoTitle: SEO_TITLE,
    seoDescription: "Shimpz は選んだ LLM を使ってレビュー済みの Assistant をあなたのコンピューター上で連携させ、大切なことに集中できるようにします。",
    title: { accent: "仕事は私が引き受けます。", remainder: "", secondLine: "あなたは大切なことに集中できます。" },
  },
  ar: {
    seoTitle: SEO_TITLE,
    seoDescription: "ينسّق Shimpz Assistants خضعت للمراجعة على حاسوبك باستخدام LLM الذي تختاره، لتتمكن من التركيز على ما يهم.",
    title: { accent: "أنجز العمل", remainder: "لتتمكن من", secondLine: "التركيز على ما يهم." },
  },
} satisfies Record<Locale, HomepageContent>;

export function homepage(locale: Locale): HomepageContent {
  return CONTENT[locale];
}
