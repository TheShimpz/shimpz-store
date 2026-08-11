import type { Locale } from "$lib/locales";

export type HomepageFeature = { title: string; body: string };

export type HomepageHumanRequests = {
  heading: string;
  body: string;
  sdkSummary: string;
  sdkCta: string;
  menuLabel: string;
  interfaceLabel: string;
  imageAlt: string;
  groupNotes: {
    approval: string;
    input: string;
    auth: string;
  };
};

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  title: string;
  lead: string;
  meetAssistants: string;
  watchMeWork: string;
  humanRequests: HomepageHumanRequests;
  usersHeading: string;
  usersBody: string;
  userFeatures: [HomepageFeature, HomepageFeature, HomepageFeature];
  catalogHeading: string;
  assistantZero: string;
  assistantSingular: string;
  assistantPlural: string;
  catalogCountTemplate: string;
  catalogCountZeroTemplate: string;
  catalogCountSingularTemplate: string;
  catalogCore: string;
  catalogUnavailable: string;
  catalogRetry: string;
  catalogCta: string;
  developersHeading: string;
  developersBody: string;
  developerFeatures: [HomepageFeature, HomepageFeature, HomepageFeature];
  developersCta: string;
};

const CONTENT = {
  en: {
    seoTitle: "Give me a goal and my assistants do the work on your computer · Shimpz",
    seoDescription: "Give me a goal and I orchestrate reviewed assistants on your computer, with the LLM you choose.",
    title: "Give me a goal and my assistants do the work on your computer",
    lead: "No agents. No code. Just a team. Assistants that already work — with the LLM you choose.",
    meetAssistants: "Meet my assistants",
    watchMeWork: "See how I ask",
    humanRequests: {
      heading: "I ask before I act.",
      body: "When an Assistant needs your decision, a missing value, or fresh authentication, I pause its Power and ask you directly. Every request is bound to that exact Assistant, Power, and action.",
      sdkSummary: "My SDK gives Creators three calls and 11 closed request kinds. Assistants cannot invent forms or authentication ceremonies at runtime.",
      sdkCta: "Explore my SDK on GitHub",
      menuLabel: "Power human request kinds",
      interfaceLabel: "Real interface",
      imageAlt: "Shimpz interface showing",
      groupNotes: {
        approval: "I record your decision for one described action. Approval is attributable, one-use, and bound to the exact request.",
        input: "I render one closed, bounded field. input:password is only for a third-party secret deliberately delivered to the named Assistant — never your Shimpz password.",
        auth: "I run the trusted authentication ceremony. Passwords, authenticator codes, and passkey evidence never enter Assistant code.",
      },
    },
    usersHeading: "What I do for you",
    usersBody: "Give me a goal and I'll put the right assistants on it. I orchestrate, they execute — all on your machine.",
    userFeatures: [
      { title: "I don't improvise", body: "Every assistant I use follows a strict spec and is manually reviewed before it ships. Nothing is generated at runtime." },
      { title: "I keep teams apart", body: "Each team runs in its own containers, with its own assistants and its own context." },
      { title: "I run where you are", body: "Self-hosted, with the LLM you choose. Your data never leaves your machine." },
    ],
    catalogHeading: "Assistants I can work with",
    assistantZero: "assistants",
    assistantSingular: "assistant",
    assistantPlural: "assistants",
    catalogCountTemplate: "{count} {noun} I can work with",
    catalogCountZeroTemplate: "{count} {noun} I can work with",
    catalogCountSingularTemplate: "{count} {noun} I can work with",
    catalogCore: "Core",
    catalogUnavailable: "I can't load my assistant catalog right now.",
    catalogRetry: "Ask me again",
    catalogCta: "See the full catalog",
    developersHeading: "Build one I can use",
    developersBody: "Write your assistant once, against a strict spec. Pass review, publish it, and get paid every time a team installs it. Users never touch your code — I handle the orchestration.",
    developerFeatures: [
      { title: "Spec and review", body: "A strict standard and manual validation before anything ships." },
      { title: "Billing built in", body: "Installs are metered and paid out." },
      { title: "Isolated runtime", body: "Your assistant runs in its own container. No infra to manage." },
    ],
    developersCta: "Read the spec",
  },
  pt: {
    seoTitle: "Dê-me um objetivo e meus assistentes fazem o trabalho no seu computador · Shimpz",
    seoDescription: "Dê-me um objetivo e eu orquestro assistentes revisados no seu computador, com a LLM que você escolher.",
    title: "Dê-me um objetivo e meus assistentes fazem o trabalho no seu computador",
    lead: "Sem agents. Sem código. Só um time. Assistentes que já funcionam — com a LLM que você escolher.",
    meetAssistants: "Conheça meus assistentes",
    watchMeWork: "Veja como eu pergunto",
    humanRequests: {
      heading: "Eu pergunto antes de agir.",
      body: "Quando um Assistente precisa da sua decisão, de um valor ausente ou de uma nova autenticação, eu pauso o Power e pergunto diretamente a você. Cada solicitação fica vinculada ao Assistente, ao Power e à ação exatos.",
      sdkSummary: "Minha SDK oferece aos Creators três chamadas e 11 tipos fechados de solicitação. Assistentes não podem inventar formulários nem cerimônias de autenticação em runtime.",
      sdkCta: "Explore minha SDK no GitHub",
      menuLabel: "Tipos de solicitação humana de Power",
      interfaceLabel: "Interface real",
      imageAlt: "Interface da Shimpz mostrando",
      groupNotes: {
        approval: "Eu registro sua decisão para uma ação descrita. A aprovação é atribuível, de uso único e vinculada à solicitação exata.",
        input: "Eu apresento um campo fechado e limitado. input:password serve apenas para um segredo de terceiro entregue intencionalmente ao Assistente identificado — nunca para sua senha da Shimpz.",
        auth: "Eu conduzo a cerimônia de autenticação confiável. Senhas, códigos de autenticador e evidências de passkey nunca entram no código do Assistente.",
      },
    },
    usersHeading: "O que eu faço por você",
    usersBody: "Dê-me um objetivo e eu colocarei os assistentes certos nele. Eu orquestro, eles executam — tudo na sua máquina.",
    userFeatures: [
      { title: "Eu não improviso", body: "Todo assistente que uso segue uma spec rigorosa e é revisado manualmente antes de ser publicado. Nada é gerado em runtime." },
      { title: "Eu mantenho os times separados", body: "Cada time roda em seus próprios containers, com seus próprios assistentes e seu próprio contexto." },
      { title: "Eu rodo onde você está", body: "Self-hosted, com a LLM que você escolher. Seus dados nunca saem da sua máquina." },
    ],
    catalogHeading: "Assistentes com quem posso trabalhar",
    assistantZero: "assistentes",
    assistantSingular: "assistente",
    assistantPlural: "assistentes",
    catalogCountTemplate: "{count} {noun} com quem posso trabalhar",
    catalogCountZeroTemplate: "{count} {noun} com quem posso trabalhar",
    catalogCountSingularTemplate: "{count} {noun} com quem posso trabalhar",
    catalogCore: "Core",
    catalogUnavailable: "Não consigo carregar meu catálogo de assistentes agora.",
    catalogRetry: "Pergunte novamente",
    catalogCta: "Veja o catálogo completo",
    developersHeading: "Crie um que eu possa usar",
    developersBody: "Escreva seu assistente uma vez, seguindo uma spec rigorosa. Passe pela revisão, publique e receba sempre que um time o instalar. Os usuários nunca tocam no seu código — eu cuido da orquestração.",
    developerFeatures: [
      { title: "Spec e revisão", body: "Um padrão rigoroso e validação manual antes de qualquer publicação." },
      { title: "Cobrança integrada", body: "As instalações são contabilizadas e os valores são repassados." },
      { title: "Runtime isolado", body: "Seu assistente roda no próprio container. Nenhuma infra para gerenciar." },
    ],
    developersCta: "Leia a spec",
  },
  es: {
    seoTitle: "Dame un objetivo y mis asistentes hacen el trabajo en tu ordenador · Shimpz",
    seoDescription: "Dame un objetivo y orquesto asistentes revisados en tu ordenador, con el LLM que elijas.",
    title: "Dame un objetivo y mis asistentes hacen el trabajo en tu ordenador",
    lead: "Sin agentes. Sin código. Solo un team. Asistentes que ya funcionan — con el LLM que elijas.",
    meetAssistants: "Conoce a mis asistentes",
    watchMeWork: "Mira cómo pregunto",
    humanRequests: {
      heading: "Pregunto antes de actuar.",
      body: "Cuando un Assistant necesita tu decisión, un dato que falta o una autenticación reciente, pauso su Power y te pregunto directamente. Cada solicitud queda vinculada a ese Assistant, Power y acción exactos.",
      sdkSummary: "Mi SDK ofrece a los Creators tres llamadas y 11 tipos cerrados de solicitud. Los Assistants no pueden inventar formularios ni ceremonias de autenticación en runtime.",
      sdkCta: "Explora mi SDK en GitHub",
      menuLabel: "Tipos de solicitud humana de Power",
      interfaceLabel: "Interfaz real",
      imageAlt: "Interfaz de Shimpz mostrando",
      groupNotes: {
        approval: "Registro tu decisión para una acción descrita. La aprobación es atribuible, de un solo uso y está vinculada a la solicitud exacta.",
        input: "Presento un campo cerrado y acotado. input:password sirve únicamente para un secreto de terceros entregado deliberadamente al Assistant indicado — nunca para tu contraseña de Shimpz.",
        auth: "Ejecuto la ceremonia de autenticación de confianza. Las contraseñas, los códigos del autenticador y la evidencia de passkey nunca entran en el código del Assistant.",
      },
    },
    usersHeading: "Lo que hago por ti",
    usersBody: "Dame un objetivo y pondré a los asistentes adecuados a trabajar en él. Yo orquesto, ellos ejecutan — todo en tu máquina.",
    userFeatures: [
      { title: "No improviso", body: "Cada asistente que uso sigue una spec estricta y se revisa manualmente antes de publicarse. Nada se genera en runtime." },
      { title: "Mantengo los teams separados", body: "Cada team se ejecuta en sus propios contenedores, con sus propios asistentes y su propio contexto." },
      { title: "Me ejecuto donde tú estás", body: "Self-hosted, con el LLM que elijas. Tus datos nunca salen de tu máquina." },
    ],
    catalogHeading: "Asistentes con los que puedo trabajar",
    assistantZero: "asistentes",
    assistantSingular: "asistente",
    assistantPlural: "asistentes",
    catalogCountTemplate: "{count} {noun} con los que puedo trabajar",
    catalogCountZeroTemplate: "{count} {noun} con los que puedo trabajar",
    catalogCountSingularTemplate: "{count} {noun} con el que puedo trabajar",
    catalogCore: "Core",
    catalogUnavailable: "Ahora mismo no puedo cargar mi catálogo de asistentes.",
    catalogRetry: "Pregúntame de nuevo",
    catalogCta: "Ver el catálogo completo",
    developersHeading: "Crea uno que pueda usar",
    developersBody: "Escribe tu asistente una vez, según una spec estricta. Supera la revisión, publícalo y cobra cada vez que un team lo instale. Los usuarios nunca tocan tu código — yo me encargo de la orquestación.",
    developerFeatures: [
      { title: "Spec y revisión", body: "Un estándar estricto y validación manual antes de que nada se publique." },
      { title: "Facturación integrada", body: "Las instalaciones se contabilizan y se pagan." },
      { title: "Runtime aislado", body: "Tu asistente se ejecuta en su propio contenedor. Sin infraestructura que gestionar." },
    ],
    developersCta: "Lee la spec",
  },
  fr: {
    seoTitle: "Donnez-moi un objectif et mes assistants font le travail sur votre ordinateur · Shimpz",
    seoDescription: "Donnez-moi un objectif et j’orchestre des assistants vérifiés sur votre ordinateur, avec le LLM de votre choix.",
    title: "Donnez-moi un objectif et mes assistants font le travail sur votre ordinateur",
    lead: "Pas d’agents. Pas de code. Juste une team. Des assistants déjà opérationnels — avec le LLM de votre choix.",
    meetAssistants: "Découvrez mes assistants",
    watchMeWork: "Voyez comment je demande",
    humanRequests: {
      heading: "Je demande avant d’agir.",
      body: "Lorsqu’un Assistant a besoin de votre décision, d’une valeur manquante ou d’une authentification récente, je mets son Power en pause et je vous interroge directement. Chaque demande est liée à cet Assistant, ce Power et cette action précis.",
      sdkSummary: "Mon SDK propose aux Creators trois appels et 11 types fermés de demandes. Les Assistants ne peuvent pas inventer de formulaires ni de cérémonies d’authentification au runtime.",
      sdkCta: "Explorer mon SDK sur GitHub",
      menuLabel: "Types de demandes humaines de Power",
      interfaceLabel: "Interface réelle",
      imageAlt: "Interface Shimpz présentant",
      groupNotes: {
        approval: "J’enregistre votre décision pour une action décrite. L’approbation est attribuable, à usage unique et liée à la demande exacte.",
        input: "J’affiche un champ fermé et borné. input:password sert uniquement à un secret tiers remis volontairement à l’Assistant nommé — jamais à votre mot de passe Shimpz.",
        auth: "J’exécute la cérémonie d’authentification de confiance. Les mots de passe, codes d’authentification et preuves de passkey n’entrent jamais dans le code de l’Assistant.",
      },
    },
    usersHeading: "Ce que je fais pour vous",
    usersBody: "Donnez-moi un objectif et je mobiliserai les bons assistants. J’orchestre, ils exécutent — le tout sur votre machine.",
    userFeatures: [
      { title: "Je n’improvise pas", body: "Chaque assistant que j’utilise suit une spec stricte et fait l’objet d’une vérification manuelle avant publication. Rien n’est généré au runtime." },
      { title: "Je sépare les teams", body: "Chaque team s’exécute dans ses propres conteneurs, avec ses propres assistants et son propre contexte." },
      { title: "Je fonctionne là où vous êtes", body: "Self-hosted, avec le LLM de votre choix. Vos données ne quittent jamais votre machine." },
    ],
    catalogHeading: "Assistants avec lesquels je peux travailler",
    assistantZero: "assistant",
    assistantSingular: "assistant",
    assistantPlural: "assistants",
    catalogCountTemplate: "{count} {noun} avec lesquels je peux travailler",
    catalogCountZeroTemplate: "{count} {noun} avec lequel je peux travailler",
    catalogCountSingularTemplate: "{count} {noun} avec lequel je peux travailler",
    catalogCore: "Core",
    catalogUnavailable: "Je ne peux pas charger mon catalogue d’assistants pour le moment.",
    catalogRetry: "Me le redemander",
    catalogCta: "Voir le catalogue complet",
    developersHeading: "Créez-en un que je puisse utiliser",
    developersBody: "Écrivez votre assistant une fois, selon une spec stricte. Passez la vérification, publiez-le et soyez rémunéré chaque fois qu’une team l’installe. Les utilisateurs ne touchent jamais à votre code — je gère l’orchestration.",
    developerFeatures: [
      { title: "Spec et vérification", body: "Un standard strict et une validation manuelle avant toute publication." },
      { title: "Facturation intégrée", body: "Les installations sont comptabilisées et rémunérées." },
      { title: "Runtime isolé", body: "Votre assistant s’exécute dans son propre conteneur. Aucune infrastructure à gérer." },
    ],
    developersCta: "Lire la spec",
  },
  de: {
    seoTitle: "Gib mir ein Ziel und meine Assistants erledigen die Arbeit auf deinem Computer · Shimpz",
    seoDescription: "Gib mir ein Ziel und ich orchestriere geprüfte Assistants auf deinem Computer, mit dem LLM deiner Wahl.",
    title: "Gib mir ein Ziel und meine Assistants erledigen die Arbeit auf deinem Computer",
    lead: "Keine Agents. Kein Code. Nur ein Team. Assistants, die bereits funktionieren — mit dem LLM deiner Wahl.",
    meetAssistants: "Lerne meine Assistants kennen",
    watchMeWork: "Sieh, wie ich nachfrage",
    humanRequests: {
      heading: "Ich frage, bevor ich handle.",
      body: "Wenn ein Assistant deine Entscheidung, einen fehlenden Wert oder eine frische Authentifizierung benötigt, pausiere ich seinen Power und frage dich direkt. Jede Anfrage ist an genau diesen Assistant, Power und diese Aktion gebunden.",
      sdkSummary: "Mein SDK bietet Creators drei Aufrufe und 11 geschlossene Anfragearten. Assistants können zur Runtime keine Formulare oder Authentifizierungsverfahren erfinden.",
      sdkCta: "Mein SDK auf GitHub erkunden",
      menuLabel: "Arten menschlicher Power-Anfragen",
      interfaceLabel: "Echte Oberfläche",
      imageAlt: "Shimpz-Oberfläche für",
      groupNotes: {
        approval: "Ich erfasse deine Entscheidung für eine beschriebene Aktion. Die Freigabe ist zurechenbar, einmalig und an die exakte Anfrage gebunden.",
        input: "Ich zeige ein geschlossenes, begrenztes Feld. input:password ist ausschließlich für ein bewusst an den benannten Assistant übergebenes Drittanbieter-Geheimnis bestimmt — niemals für dein Shimpz-Passwort.",
        auth: "Ich führe das vertrauenswürdige Authentifizierungsverfahren aus. Passwörter, Authenticator-Codes und Passkey-Nachweise gelangen nie in den Assistant-Code.",
      },
    },
    usersHeading: "Was ich für dich tue",
    usersBody: "Gib mir ein Ziel und ich setze die richtigen Assistants darauf an. Ich orchestriere, sie führen aus — alles auf deinem Rechner.",
    userFeatures: [
      { title: "Ich improvisiere nicht", body: "Jeder Assistant, den ich verwende, folgt einer strikten Spec und wird vor der Veröffentlichung manuell geprüft. Zur Runtime wird nichts generiert." },
      { title: "Ich halte Teams getrennt", body: "Jedes Team läuft in eigenen Containern, mit eigenen Assistants und eigenem Kontext." },
      { title: "Ich laufe dort, wo du bist", body: "Self-hosted, mit dem LLM deiner Wahl. Deine Daten verlassen deinen Rechner nie." },
    ],
    catalogHeading: "Assistants, mit denen ich arbeiten kann",
    assistantZero: "Assistants",
    assistantSingular: "Assistant",
    assistantPlural: "Assistants",
    catalogCountTemplate: "{count} {noun}, mit denen ich arbeiten kann",
    catalogCountZeroTemplate: "{count} {noun}, mit denen ich arbeiten kann",
    catalogCountSingularTemplate: "{count} {noun}, mit dem ich arbeiten kann",
    catalogCore: "Core",
    catalogUnavailable: "Ich kann meinen Assistant-Katalog gerade nicht laden.",
    catalogRetry: "Frag mich erneut",
    catalogCta: "Den vollständigen Katalog ansehen",
    developersHeading: "Baue einen, den ich nutzen kann",
    developersBody: "Schreibe deinen Assistant einmal nach einer strikten Spec. Bestehe die Prüfung, veröffentliche ihn und werde jedes Mal bezahlt, wenn ein Team ihn installiert. Nutzer berühren deinen Code nie — ich übernehme die Orchestrierung.",
    developerFeatures: [
      { title: "Spec und Prüfung", body: "Ein strikter Standard und manuelle Validierung, bevor etwas veröffentlicht wird." },
      { title: "Abrechnung integriert", body: "Installationen werden erfasst und ausgezahlt." },
      { title: "Isolierte Runtime", body: "Dein Assistant läuft in seinem eigenen Container. Keine Infrastruktur zu verwalten." },
    ],
    developersCta: "Spec lesen",
  },
  zh: {
    seoTitle: "给我一个目标，我的 Assistant 就会在你的电脑上完成工作 · Shimpz",
    seoDescription: "给我一个目标，我会在你的电脑上编排经过审核的 Assistant，并使用你选择的 LLM。",
    title: "给我一个目标，我的 Assistant 就会在你的电脑上完成工作",
    lead: "无需 Agent。无需代码。只需一个 Team。开箱即用的 Assistant — 搭配你选择的 LLM。",
    meetAssistants: "认识我的 Assistant",
    watchMeWork: "看看我如何询问",
    humanRequests: {
      heading: "行动之前，我会先询问你。",
      body: "当 Assistant 需要你的决定、缺失的值或新的身份验证时，我会暂停它的 Power 并直接询问你。每个请求都与确切的 Assistant、Power 和操作绑定。",
      sdkSummary: "我的 SDK 为 Creator 提供 3 个调用和 11 种封闭的请求类型。Assistant 无法在 runtime 临时发明表单或身份验证流程。",
      sdkCta: "在 GitHub 上查看我的 SDK",
      menuLabel: "Power 人工请求类型",
      interfaceLabel: "真实界面",
      imageAlt: "Shimpz 界面正在显示",
      groupNotes: {
        approval: "我会记录你对一项明确操作的决定。批准可归因、仅使用一次，并与确切请求绑定。",
        input: "我会呈现一个封闭且有界的字段。input:password 仅用于你有意交给指定 Assistant 的第三方秘密 — 绝不是你的 Shimpz 密码。",
        auth: "我负责执行可信的身份验证流程。密码、验证器代码和 passkey 证明绝不会进入 Assistant 代码。",
      },
    },
    usersHeading: "我能为你做什么",
    usersBody: "给我一个目标，我会让合适的 Assistant 来处理。我负责编排，它们负责执行 — 全部在你的机器上。",
    userFeatures: [
      { title: "我不临场发挥", body: "我使用的每个 Assistant 都遵循严格的 Spec，并在发布前经过人工审核。Runtime 不会生成任何代码。" },
      { title: "我让 Team 彼此隔离", body: "每个 Team 都在自己的容器中运行，拥有自己的 Assistant 和上下文。" },
      { title: "我就在你所在之处运行", body: "Self-hosted，使用你选择的 LLM。你的数据绝不会离开你的机器。" },
    ],
    catalogHeading: "我可以协作的 Assistant",
    assistantZero: "个 Assistant",
    assistantSingular: "个 Assistant",
    assistantPlural: "个 Assistant",
    catalogCountTemplate: "我可以协作的 {count}{noun}",
    catalogCountZeroTemplate: "我可以协作的 {count}{noun}",
    catalogCountSingularTemplate: "我可以协作的 {count}{noun}",
    catalogCore: "Core",
    catalogUnavailable: "我现在无法加载我的 Assistant 目录。",
    catalogRetry: "再问我一次",
    catalogCta: "查看完整目录",
    developersHeading: "构建一个我能使用的 Assistant",
    developersBody: "按照严格的 Spec，一次编写你的 Assistant。通过审核并发布后，每当一个 Team 安装它，你都能获得收入。用户无需接触你的代码 — 编排由我负责。",
    developerFeatures: [
      { title: "Spec 与审核", body: "在任何内容发布前，都要遵循严格标准并经过人工验证。" },
      { title: "内置计费", body: "安装会被计量并结算。" },
      { title: "隔离 Runtime", body: "你的 Assistant 在自己的容器中运行。无需管理基础设施。" },
    ],
    developersCta: "阅读 Spec",
  },
  ja: {
    seoTitle: "目標を教えてくれれば、私の Assistant があなたのコンピューターで作業します · Shimpz",
    seoDescription: "目標を教えてください。選んだ LLM を使い、レビュー済みの Assistant をあなたのコンピューター上で編成します。",
    title: "目標を教えてくれれば、私の Assistant があなたのコンピューターで作業します",
    lead: "Agent もコードも不要。必要なのは Team だけ。選んだ LLM で、すでに動く Assistant を使えます。",
    meetAssistants: "私の Assistant を見る",
    watchMeWork: "私の確認方法を見る",
    humanRequests: {
      heading: "行動する前に、私はあなたに確認します。",
      body: "Assistant があなたの判断、不足している値、または新しい認証を必要とするとき、私はその Power を一時停止して直接確認します。各リクエストは、正確な Assistant、Power、操作に結び付けられます。",
      sdkSummary: "私の SDK は Creator に 3 つの呼び出しと 11 種類の閉じたリクエストを提供します。Assistant が runtime でフォームや認証手順を勝手に作ることはできません。",
      sdkCta: "GitHub で私の SDK を見る",
      menuLabel: "Power の人間向けリクエスト種別",
      interfaceLabel: "実際のインターフェース",
      imageAlt: "次を表示する Shimpz インターフェース:",
      groupNotes: {
        approval: "私は、説明された 1 つの操作に対するあなたの判断を記録します。承認は帰属可能で 1 回限り、正確なリクエストに結び付けられます。",
        input: "私は閉じた範囲付きフィールドを表示します。input:password は、指定された Assistant に意図的に渡す第三者の秘密専用です。Shimpz のパスワードには決して使いません。",
        auth: "信頼された認証手順は私が実行します。パスワード、認証コード、passkey の証明が Assistant のコードに入ることはありません。",
      },
    },
    usersHeading: "私ができること",
    usersBody: "目標を教えてください。最適な Assistant を割り当てます。私が編成し、Assistant が実行します — すべてあなたのマシン上で。",
    userFeatures: [
      { title: "私は即興で作りません", body: "私が使うすべての Assistant は厳格な Spec に従い、公開前に人の手でレビューされます。Runtime では何も生成されません。" },
      { title: "Team を分離します", body: "各 Team は専用コンテナで実行され、独自の Assistant とコンテキストを持ちます。" },
      { title: "あなたのいる場所で動きます", body: "Self-hosted で、選んだ LLM を使います。データがあなたのマシンを離れることはありません。" },
    ],
    catalogHeading: "私が連携できる Assistant",
    assistantZero: "件の Assistant",
    assistantSingular: "件の Assistant",
    assistantPlural: "件の Assistant",
    catalogCountTemplate: "私が連携できる {count}{noun}",
    catalogCountZeroTemplate: "私が連携できる {count}{noun}",
    catalogCountSingularTemplate: "私が連携できる {count}{noun}",
    catalogCore: "Core",
    catalogUnavailable: "現在、私の Assistant カタログを読み込めません。",
    catalogRetry: "もう一度聞く",
    catalogCta: "カタログをすべて見る",
    developersHeading: "私が使えるものを作る",
    developersBody: "厳格な Spec に沿って Assistant を一度だけ書きます。レビューを通過して公開すれば、Team がインストールするたびに報酬を得られます。ユーザーはコードに触れません — オーケストレーションは私が担います。",
    developerFeatures: [
      { title: "Spec とレビュー", body: "公開前に厳格な標準と人による検証を適用します。" },
      { title: "組み込みの課金", body: "インストールは計測され、収益が支払われます。" },
      { title: "分離された Runtime", body: "Assistant は専用コンテナで動作します。管理するインフラはありません。" },
    ],
    developersCta: "Spec を読む",
  },
  ar: {
    seoTitle: "أعطني هدفًا وستنجز Assistants الخاصة بي العمل على حاسوبك · Shimpz",
    seoDescription: "أعطني هدفًا وسأنسّق Assistants خضعت للمراجعة على حاسوبك، باستخدام LLM الذي تختاره.",
    title: "أعطني هدفًا وستنجز Assistants الخاصة بي العمل على حاسوبك",
    lead: "لا Agents. لا كود. فقط Team. Assistants تعمل بالفعل — مع LLM الذي تختاره.",
    meetAssistants: "تعرّف إلى Assistants الخاصة بي",
    watchMeWork: "شاهد كيف أطلب قرارك",
    humanRequests: {
      heading: "أسألك قبل أن أتصرف.",
      body: "عندما تحتاج Assistant إلى قرارك أو قيمة ناقصة أو مصادقة حديثة، أوقف Power الخاص بها مؤقتًا وأسألك مباشرة. يرتبط كل طلب بتلك Assistant وPower والإجراء المحدد بدقة.",
      sdkSummary: "تمنح SDK الخاصة بي Creators ثلاث استدعاءات و11 نوعًا مغلقًا من الطلبات. لا تستطيع Assistants اختراع نماذج أو مراسم مصادقة أثناء Runtime.",
      sdkCta: "استكشف SDK الخاصة بي على GitHub",
      menuLabel: "أنواع طلبات Power البشرية",
      interfaceLabel: "واجهة حقيقية",
      imageAlt: "واجهة Shimpz تعرض",
      groupNotes: {
        approval: "أسجّل قرارك لإجراء موصوف واحد. تكون الموافقة منسوبة إليك، صالحة لمرة واحدة، ومرتبطة بالطلب المحدد.",
        input: "أعرض حقلًا مغلقًا ومحدودًا. يُستخدم input:password فقط لسر تابع لطرف ثالث تسلّمه عمدًا إلى Assistant المحددة — وليس لكلمة مرور Shimpz أبدًا.",
        auth: "أنا أنفذ مراسم المصادقة الموثوقة. لا تدخل كلمات المرور أو رموز تطبيق المصادقة أو أدلة passkey إلى كود Assistant أبدًا.",
      },
    },
    usersHeading: "ما أفعله من أجلك",
    usersBody: "أعطني هدفًا وسأضع Assistants المناسبة للعمل عليه. أنا أنسّق وهي تنفّذ — كل ذلك على جهازك.",
    userFeatures: [
      { title: "أنا لا أرتجل", body: "كل Assistant أستخدمها تتبع Spec صارمة وتخضع لمراجعة يدوية قبل النشر. لا يُولّد شيء أثناء Runtime." },
      { title: "أُبقي Teams منفصلة", body: "تعمل كل Team في حاوياتها الخاصة، مع Assistants وسياق خاصين بها." },
      { title: "أعمل حيث تكون", body: "Self-hosted، مع LLM الذي تختاره. لا تغادر بياناتك جهازك أبدًا." },
    ],
    catalogHeading: "Assistants التي يمكنني العمل معها",
    assistantZero: "Assistants",
    assistantSingular: "Assistant",
    assistantPlural: "Assistants",
    catalogCountTemplate: "{count} {noun} يمكنني العمل معها",
    catalogCountZeroTemplate: "{count} {noun} يمكنني العمل معها",
    catalogCountSingularTemplate: "{count} {noun} يمكنني العمل معها",
    catalogCore: "Core",
    catalogUnavailable: "لا يمكنني تحميل كتالوج Assistants الخاص بي الآن.",
    catalogRetry: "اسألني مجددًا",
    catalogCta: "شاهد الكتالوج الكامل",
    developersHeading: "أنشئ واحدة يمكنني استخدامها",
    developersBody: "اكتب Assistant الخاصة بك مرة واحدة وفق Spec صارمة. اجتز المراجعة وانشرها واحصل على المال كلما ثبّتها Team. لا يلمس المستخدمون الكود الخاص بك — أنا أتولى التنسيق.",
    developerFeatures: [
      { title: "Spec ومراجعة", body: "معيار صارم وتحقق يدوي قبل نشر أي شيء." },
      { title: "فوترة مدمجة", body: "تُقاس عمليات التثبيت وتُدفع عوائدها." },
      { title: "Runtime معزول", body: "تعمل Assistant الخاصة بك في حاويتها المنفصلة. لا بنية تحتية لإدارتها." },
    ],
    developersCta: "اقرأ Spec",
  },
} satisfies Record<Locale, HomepageContent>;

export function homepage(locale: Locale): HomepageContent {
  return CONTENT[locale];
}

export function formatCatalogCount(content: HomepageContent, count: number): string {
  const noun = count === 0
    ? content.assistantZero
    : count === 1
      ? content.assistantSingular
      : content.assistantPlural;
  const template = count === 0
    ? content.catalogCountZeroTemplate
    : count === 1
      ? content.catalogCountSingularTemplate
      : content.catalogCountTemplate;
  return template
    .replace("{count}", () => String(count))
    .replace("{noun}", () => noun);
}
