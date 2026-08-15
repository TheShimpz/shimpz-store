import type { Locale } from "$lib/locales";

export type HomepageFeature = { title: string; body: string };

export const HOMEPAGE_TASK_TYPING_DELAY_MS = 27;
export const HOMEPAGE_TASK_HOLD_MS = 900;

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  intro: string;
  title: string;
  lead: string;
  meetAssistants: string;
  taskPlaceholder: string;
  taskExamples: readonly [string, string, string];
  taskAnimationPause: string;
  taskAnimationResume: string;
  taskLabel: string;
  taskSubmit: string;
  taskStorageError: string;
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
    seoTitle: "Shimpz · Reviewed assistants that work on your computer",
    seoDescription: "Shimpz coordinates reviewed assistants on your computer, with the LLM you choose, so you can focus on what matters.",
    intro: "Hello, I'm Shimpz!",
    title: "I do the work so you can focus on what matters.",
    lead: "Type your first task below and see what I can do:",
    meetAssistants: "Meet my assistants",
    taskPlaceholder: "Describe the result you need...",
    taskExamples: [
      "Turn these campaign results into my next actions...",
      "Map how our lead forms, CRM, and reports should connect...",
      "Build next week's campaign task plan...",
    ],
    taskAnimationPause: "Pause examples",
    taskAnimationResume: "Resume examples",
    taskLabel: "Your first task",
    taskSubmit: "Start",
    taskStorageError: "I couldn't keep this task in your browser. Try again.",
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
    seoTitle: "Shimpz · Assistentes revisados que trabalham no seu computador",
    seoDescription: "O Shimpz coordena assistentes revisados no seu computador, com a LLM que você escolher, para que você se concentre no que importa.",
    intro: "Olá, eu sou Shimpz!",
    title: "Eu executo o trabalho para que você possa se concentrar no que importa.",
    lead: "Digite sua primeira tarefa abaixo e veja o que eu posso fazer:",
    meetAssistants: "Conheça meus assistentes",
    taskPlaceholder: "Descreva o resultado que você precisa...",
    taskExamples: [
      "Transforme estes resultados de campanha nas minhas próximas ações...",
      "Mapeie como formulários, CRM e relatórios devem se conectar...",
      "Crie o plano de tarefas da campanha da próxima semana...",
    ],
    taskAnimationPause: "Pausar exemplos",
    taskAnimationResume: "Retomar exemplos",
    taskLabel: "Sua primeira tarefa",
    taskSubmit: "Começar",
    taskStorageError: "Não consegui manter esta tarefa no seu navegador. Tente novamente.",
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
    seoTitle: "Shimpz · Asistentes revisados que trabajan en tu ordenador",
    seoDescription: "Shimpz coordina asistentes revisados en tu ordenador, con el LLM que elijas, para que te centres en lo que importa.",
    intro: "¡Hola, soy Shimpz!",
    title: "Hago el trabajo para que puedas concentrarte en lo que importa.",
    lead: "Escribe tu primera tarea abajo y descubre lo que puedo hacer:",
    meetAssistants: "Conoce a mis asistentes",
    taskPlaceholder: "Describe el resultado que necesitas...",
    taskExamples: [
      "Convierte estos resultados de campaña en mis próximas acciones...",
      "Define cómo deben conectarse formularios, CRM e informes...",
      "Crea el plan de tareas de campaña para la próxima semana...",
    ],
    taskAnimationPause: "Pausar ejemplos",
    taskAnimationResume: "Reanudar ejemplos",
    taskLabel: "Tu primera tarea",
    taskSubmit: "Empezar",
    taskStorageError: "No pude guardar esta tarea en tu navegador. Inténtalo de nuevo.",
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
    seoTitle: "Shimpz · Des assistants vérifiés qui travaillent sur votre ordinateur",
    seoDescription: "Shimpz coordonne des assistants vérifiés sur votre ordinateur, avec le LLM de votre choix, pour vous laisser vous concentrer sur l’essentiel.",
    intro: "Bonjour, je suis Shimpz !",
    title: "J’exécute le travail pour que vous puissiez vous concentrer sur l’essentiel.",
    lead: "Saisissez votre première tâche ci-dessous et découvrez ce que je peux faire :",
    meetAssistants: "Découvrez mes assistants",
    taskPlaceholder: "Décrivez le résultat dont vous avez besoin...",
    taskExamples: [
      "Transformez ces résultats de campagne en mes prochaines actions...",
      "Définissez comment connecter formulaires, CRM et rapports...",
      "Créez le plan de campagne de la semaine prochaine...",
    ],
    taskAnimationPause: "Mettre les exemples en pause",
    taskAnimationResume: "Reprendre les exemples",
    taskLabel: "Votre première tâche",
    taskSubmit: "Commencer",
    taskStorageError: "Je n’ai pas pu conserver cette tâche dans votre navigateur. Réessayez.",
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
    seoTitle: "Shimpz · Geprüfte Assistants, die auf deinem Computer arbeiten",
    seoDescription: "Shimpz koordiniert geprüfte Assistants auf deinem Computer mit dem LLM deiner Wahl, damit du dich auf das Wesentliche konzentrieren kannst.",
    intro: "Hallo, ich bin Shimpz!",
    title: "Ich erledige die Arbeit, damit du dich auf das Wesentliche konzentrieren kannst.",
    lead: "Gib unten deine erste Aufgabe ein und sieh, was ich tun kann:",
    meetAssistants: "Lerne meine Assistants kennen",
    taskPlaceholder: "Beschreibe das gewünschte Ergebnis...",
    taskExamples: [
      "Mach aus diesen Kampagnenergebnissen meine nächsten Schritte...",
      "Plane die Verbindung von Formularen, CRM und Berichten...",
      "Erstelle den Kampagnenplan für die nächste Woche...",
    ],
    taskAnimationPause: "Beispiele pausieren",
    taskAnimationResume: "Beispiele fortsetzen",
    taskLabel: "Deine erste Aufgabe",
    taskSubmit: "Starten",
    taskStorageError: "Ich konnte diese Aufgabe nicht in deinem Browser speichern. Versuche es erneut.",
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
    seoTitle: "Shimpz · 在你的电脑上工作的审核版 Assistant",
    seoDescription: "Shimpz 使用你选择的 LLM，在你的电脑上协调经过审核的 Assistant，让你专注于真正重要的事。",
    intro: "你好，我是 Shimpz！",
    title: "我来执行工作，让你专注于真正重要的事。",
    lead: "在下方输入你的第一个任务，看看我能做什么：",
    meetAssistants: "认识我的 Assistant",
    taskPlaceholder: "描述你需要的结果...",
    taskExamples: [
      "把这些广告活动结果变成我的下一步行动...",
      "规划表单、CRM 和报告应该如何连接...",
      "制定下周的广告活动任务计划...",
    ],
    taskAnimationPause: "暂停示例",
    taskAnimationResume: "继续示例",
    taskLabel: "你的第一个任务",
    taskSubmit: "开始",
    taskStorageError: "我无法在你的浏览器中保存此任务。请重试。",
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
    seoTitle: "Shimpz · あなたのコンピューターで働くレビュー済み Assistant",
    seoDescription: "Shimpz は選んだ LLM を使ってレビュー済みの Assistant をあなたのコンピューター上で連携させ、大切なことに集中できるようにします。",
    intro: "こんにちは、Shimpzです！",
    title: "大切なことに集中できるよう、仕事は私が実行します。",
    lead: "下に最初のタスクを入力して、私にできることを試してください：",
    meetAssistants: "私の Assistant を見る",
    taskPlaceholder: "必要な結果を説明してください...",
    taskExamples: [
      "このキャンペーン結果を次の行動にまとめて...",
      "フォーム、CRM、レポートの連携方法を整理して...",
      "来週のキャンペーンタスク計画を作って...",
    ],
    taskAnimationPause: "例を一時停止",
    taskAnimationResume: "例を再開",
    taskLabel: "最初のタスク",
    taskSubmit: "始める",
    taskStorageError: "このタスクをブラウザーに保持できませんでした。もう一度お試しください。",
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
    seoTitle: "Shimpz · Assistants خضعت للمراجعة وتعمل على حاسوبك",
    seoDescription: "ينسّق Shimpz Assistants خضعت للمراجعة على حاسوبك باستخدام LLM الذي تختاره، لتتمكن من التركيز على ما يهم.",
    intro: "مرحبًا، أنا Shimpz!",
    title: "أنفّذ العمل لتتمكن من التركيز على ما يهم.",
    lead: "اكتب مهمتك الأولى أدناه وشاهد ما يمكنني فعله:",
    meetAssistants: "تعرّف إلى Assistants الخاصة بي",
    taskPlaceholder: "صف النتيجة التي تحتاجها...",
    taskExamples: [
      "حوّل نتائج الحملة هذه إلى خطواتي التالية...",
      "خطط لكيفية ربط النماذج وCRM والتقارير...",
      "أنشئ خطة مهام الحملة للأسبوع المقبل...",
    ],
    taskAnimationPause: "إيقاف الأمثلة مؤقتًا",
    taskAnimationResume: "استئناف الأمثلة",
    taskLabel: "مهمتك الأولى",
    taskSubmit: "ابدأ",
    taskStorageError: "تعذر الاحتفاظ بهذه المهمة في متصفحك. حاول مرة أخرى.",
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
