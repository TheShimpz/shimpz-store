import type { Locale } from "$lib/locales";

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  title: string;
};

const CONTENT = {
  en: {
    seoTitle: "Shimpz · Reviewed assistants that work on your computer",
    seoDescription: "Shimpz coordinates reviewed assistants on your computer, with the LLM you choose, so you can focus on what matters.",
    title: "I do the work so you can focus on what matters.",
  },
  pt: {
    seoTitle: "Shimpz · Assistentes revisados que trabalham no seu computador",
    seoDescription: "O Shimpz coordena assistentes revisados no seu computador, com a LLM que você escolher, para que você se concentre no que importa.",
    title: "Eu executo o trabalho para que você possa se concentrar no que importa.",
  },
  es: {
    seoTitle: "Shimpz · Asistentes revisados que trabajan en tu ordenador",
    seoDescription: "Shimpz coordina asistentes revisados en tu ordenador, con el LLM que elijas, para que te centres en lo que importa.",
    title: "Hago el trabajo para que puedas concentrarte en lo que importa.",
  },
  fr: {
    seoTitle: "Shimpz · Des assistants vérifiés qui travaillent sur votre ordinateur",
    seoDescription: "Shimpz coordonne des assistants vérifiés sur votre ordinateur, avec le LLM de votre choix, pour vous laisser vous concentrer sur l’essentiel.",
    title: "J’exécute le travail pour que vous puissiez vous concentrer sur l’essentiel.",
  },
  de: {
    seoTitle: "Shimpz · Geprüfte Assistants, die auf deinem Computer arbeiten",
    seoDescription: "Shimpz koordiniert geprüfte Assistants auf deinem Computer mit dem LLM deiner Wahl, damit du dich auf das Wesentliche konzentrieren kannst.",
    title: "Ich erledige die Arbeit, damit du dich auf das Wesentliche konzentrieren kannst.",
  },
  zh: {
    seoTitle: "Shimpz · 在你的电脑上工作的审核版 Assistant",
    seoDescription: "Shimpz 使用你选择的 LLM，在你的电脑上协调经过审核的 Assistant，让你专注于真正重要的事。",
    title: "我来执行工作，让你专注于真正重要的事。",
  },
  ja: {
    seoTitle: "Shimpz · あなたのコンピューターで働くレビュー済み Assistant",
    seoDescription: "Shimpz は選んだ LLM を使ってレビュー済みの Assistant をあなたのコンピューター上で連携させ、大切なことに集中できるようにします。",
    title: "大切なことに集中できるよう、仕事は私が実行します。",
  },
  ar: {
    seoTitle: "Shimpz · Assistants خضعت للمراجعة وتعمل على حاسوبك",
    seoDescription: "ينسّق Shimpz Assistants خضعت للمراجعة على حاسوبك باستخدام LLM الذي تختاره، لتتمكن من التركيز على ما يهم.",
    title: "أنفّذ العمل لتتمكن من التركيز على ما يهم.",
  },
} satisfies Record<Locale, HomepageContent>;

export function homepage(locale: Locale): HomepageContent {
  return CONTENT[locale];
}
