import type { Locale } from "$lib/locales";

export type HomepageFeature = { title: string; body: string };

export type HomepageContent = {
  seoTitle: string;
  seoDescription: string;
  title: string;
  lead: string;
  readSpec: string;
  browseAssistants: string;
  developersHeading: string;
  developersBody: string;
  developerFeatures: [HomepageFeature, HomepageFeature, HomepageFeature];
  developersCta: string;
  catalogHeading: string;
  assistantSingular: string;
  assistantPlural: string;
  catalogGrowing: string;
  catalogCore: string;
  catalogUnavailable: string;
  catalogRetry: string;
  usersHeading: string;
  usersBody: string;
  userFeatures: [HomepageFeature, HomepageFeature, HomepageFeature];
};

type FeatureTuple = [string, string];
type HomepageTuple = [
  string, string, string, string, string, string,
  string, string, [FeatureTuple, FeatureTuple, FeatureTuple], string,
  [string, string, string, string, string, string, string],
  string, string, [FeatureTuple, FeatureTuple, FeatureTuple],
];

function buildContent(input: Record<Locale, HomepageTuple>): Record<Locale, HomepageContent> {
  return Object.fromEntries(Object.entries(input).map(([
    locale,
    [
      seoTitle, seoDescription, title, lead, readSpec, browseAssistants,
      developersHeading, developersBody, developerFeatures, developersCta,
      [catalogHeading, assistantSingular, assistantPlural, catalogGrowing, catalogCore, catalogUnavailable, catalogRetry],
      usersHeading, usersBody, userFeatures,
    ],
  ]) => [locale, {
    seoTitle,
    seoDescription,
    title,
    lead,
    readSpec,
    browseAssistants,
    developersHeading,
    developersBody,
    developerFeatures: developerFeatures.map(([featureTitle, body]) => ({ title: featureTitle, body })),
    developersCta,
    catalogHeading,
    assistantSingular,
    assistantPlural,
    catalogGrowing,
    catalogCore,
    catalogUnavailable,
    catalogRetry,
    usersHeading,
    usersBody,
    userFeatures: userFeatures.map(([featureTitle, body]) => ({ title: featureTitle, body })),
  }])) as Record<Locale, HomepageContent>;
}

const CONTENT = buildContent({
  en: [
    "Write it once. Sell it forever. · Shimpz",
    "Build a reviewed Assistant, publish it once, and make it available to every Shimpz Team.",
    "Write it once. Sell it forever.",
    "Build an assistant, pass review, publish it. Every team that installs it pays you.",
    "Read the spec", "Browse assistants",
    "For Developers",
    "Build against a strict spec, pass manual review, publish. Your assistant runs isolated in Docker — no infra for you to manage.",
    [
      ["Spec and review", "Every assistant follows a strict standard and is manually validated before it ships."],
      ["Billing built in", "Installs are metered and paid out. You write code, not invoices."],
      ["Isolated runtime", "Each assistant runs in its own container. No shared state, no surprises."],
    ],
    "Publish your first assistant",
    ["Live catalog", "assistant", "assistants", "and growing", "Core", "The live assistant catalog is temporarily unavailable.", "Retry"],
    "For Users",
    "Create a team, install the assistants it needs, and talk to it in chat — the way you'd talk to people.",
    [
      ["Reviewed, not generated", "Assistants are real code, vetted before publishing. Nothing is written on the fly."],
      ["Isolated teams", "Each team runs separately, with its own assistants and its own context."],
      ["Self-hosted", "Runs on your own infrastructure. Your data stays with you."],
    ],
  ],
  pt: [
    "Escreva uma vez. Venda para sempre. · Shimpz",
    "Crie um Assistente revisado, publique uma vez e disponibilize-o para todos os Times Shimpz.",
    "Escreva uma vez. Venda para sempre.",
    "Crie um assistente, passe pela revisão e publique. Cada time que o instala paga você.",
    "Leia a spec", "Explore assistentes",
    "Para desenvolvedores",
    "Desenvolva seguindo uma spec rigorosa, passe pela revisão manual e publique. Seu assistente roda isolado no Docker — nenhuma infraestrutura para você gerenciar.",
    [
      ["Spec e revisão", "Todo assistente segue um padrão rigoroso e é validado manualmente antes da publicação."],
      ["Cobrança integrada", "Instalações são contabilizadas e os valores são repassados. Você escreve código, não faturas."],
      ["Runtime isolado", "Cada assistente roda em seu próprio container. Sem estado compartilhado, sem surpresas."],
    ],
    "Publique seu primeiro assistente",
    ["Catálogo ao vivo", "assistente", "assistentes", "e crescendo", "Core", "O catálogo de assistentes está temporariamente indisponível.", "Tentar novamente"],
    "Para usuários",
    "Crie um time, instale os assistentes de que ele precisa e converse pelo chat — como você conversaria com pessoas.",
    [
      ["Revisado, não gerado", "Assistentes são código real, verificado antes da publicação. Nada é escrito na hora."],
      ["Times isolados", "Cada time roda separadamente, com seus próprios assistentes e seu próprio contexto."],
      ["Self-hosted", "Roda na sua própria infraestrutura. Seus dados ficam com você."],
    ],
  ],
  es: [
    "Escríbelo una vez. Véndelo para siempre. · Shimpz",
    "Crea un Asistente revisado, publícalo una vez y ponlo a disposición de todos los Teams de Shimpz.",
    "Escríbelo una vez. Véndelo para siempre.",
    "Crea un asistente, supera la revisión y publícalo. Cada team que lo instala te paga.",
    "Lee la spec", "Explora asistentes",
    "Para desarrolladores",
    "Desarrolla con una spec estricta, supera la revisión manual y publica. Tu asistente se ejecuta aislado en Docker — sin infraestructura que gestionar.",
    [
      ["Spec y revisión", "Cada asistente sigue un estándar estricto y se valida manualmente antes de publicarse."],
      ["Facturación integrada", "Las instalaciones se contabilizan y se pagan. Tú escribes código, no facturas."],
      ["Runtime aislado", "Cada asistente se ejecuta en su propio contenedor. Sin estado compartido, sin sorpresas."],
    ],
    "Publica tu primer asistente",
    ["Catálogo en vivo", "asistente", "asistentes", "y creciendo", "Core", "El catálogo de asistentes no está disponible temporalmente.", "Reintentar"],
    "Para usuarios",
    "Crea un team, instala los asistentes que necesita y habla con él por chat — como hablarías con personas.",
    [
      ["Revisado, no generado", "Los asistentes son código real, evaluado antes de publicarse. Nada se escribe sobre la marcha."],
      ["Teams aislados", "Cada team se ejecuta por separado, con sus propios asistentes y su propio contexto."],
      ["Self-hosted", "Se ejecuta en tu propia infraestructura. Tus datos se quedan contigo."],
    ],
  ],
  fr: [
    "Écrivez-le une fois. Vendez-le pour toujours. · Shimpz",
    "Créez un Assistant vérifié, publiez-le une fois et rendez-le disponible pour toutes les Teams Shimpz.",
    "Écrivez-le une fois. Vendez-le pour toujours.",
    "Créez un assistant, passez la vérification et publiez-le. Chaque team qui l’installe vous paie.",
    "Lire la spec", "Explorer les assistants",
    "Pour les développeurs",
    "Développez selon une spec stricte, passez la vérification manuelle et publiez. Votre assistant s’exécute isolé dans Docker — aucune infrastructure à gérer.",
    [
      ["Spec et vérification", "Chaque assistant suit un standard strict et est validé manuellement avant publication."],
      ["Facturation intégrée", "Les installations sont comptabilisées et rémunérées. Vous écrivez du code, pas des factures."],
      ["Runtime isolé", "Chaque assistant s’exécute dans son propre conteneur. Aucun état partagé, aucune surprise."],
    ],
    "Publiez votre premier assistant",
    ["Catalogue en direct", "assistant", "assistants", "et ce n’est qu’un début", "Core", "Le catalogue d’assistants est temporairement indisponible.", "Réessayer"],
    "Pour les utilisateurs",
    "Créez une team, installez les assistants dont elle a besoin et échangez avec elle dans le chat — comme avec des personnes.",
    [
      ["Vérifié, pas généré", "Les assistants sont du vrai code, évalué avant publication. Rien n’est écrit à la volée."],
      ["Teams isolées", "Chaque team s’exécute séparément, avec ses propres assistants et son propre contexte."],
      ["Self-hosted", "S’exécute sur votre propre infrastructure. Vos données restent chez vous."],
    ],
  ],
  de: [
    "Einmal schreiben. Für immer verkaufen. · Shimpz",
    "Entwickle einen geprüften Assistant, veröffentliche ihn einmal und stelle ihn allen Shimpz Teams bereit.",
    "Einmal schreiben. Für immer verkaufen.",
    "Entwickle einen Assistant, bestehe die Prüfung und veröffentliche ihn. Jedes Team, das ihn installiert, bezahlt dich.",
    "Spec lesen", "Assistants entdecken",
    "Für Entwickler",
    "Entwickle nach einer strikten Spec, bestehe die manuelle Prüfung und veröffentliche. Dein Assistant läuft isoliert in Docker — keine Infrastruktur für dich zu verwalten.",
    [
      ["Spec und Prüfung", "Jeder Assistant folgt einem strikten Standard und wird vor der Veröffentlichung manuell validiert."],
      ["Abrechnung integriert", "Installationen werden erfasst und ausgezahlt. Du schreibst Code, keine Rechnungen."],
      ["Isolierte Runtime", "Jeder Assistant läuft in seinem eigenen Container. Kein geteilter Zustand, keine Überraschungen."],
    ],
    "Veröffentliche deinen ersten Assistant",
    ["Live-Katalog", "Assistant", "Assistants", "und es werden mehr", "Core", "Der Assistant-Katalog ist vorübergehend nicht verfügbar.", "Erneut versuchen"],
    "Für Nutzer",
    "Erstelle ein Team, installiere die benötigten Assistants und sprich im Chat mit ihm — so, wie du mit Menschen sprichst.",
    [
      ["Geprüft, nicht generiert", "Assistants sind echter Code, der vor der Veröffentlichung geprüft wird. Nichts wird spontan geschrieben."],
      ["Isolierte Teams", "Jedes Team läuft separat, mit eigenen Assistants und eigenem Kontext."],
      ["Self-hosted", "Läuft auf deiner eigenen Infrastruktur. Deine Daten bleiben bei dir."],
    ],
  ],
  zh: [
    "编写一次，持续销售。· Shimpz", "构建经过审核的 Assistant，一次发布，供所有 Shimpz Team 使用。",
    "编写一次，持续销售。", "构建 Assistant，通过审核并发布。每个安装它的 Team 都会向你付费。",
    "阅读 Spec", "浏览 Assistant",
    "面向开发者", "按照严格的 Spec 构建，通过人工审核并发布。你的 Assistant 在 Docker 中隔离运行——无需管理基础设施。",
    [["Spec 与审核", "每个 Assistant 都遵循严格标准，并在发布前经过人工验证。"], ["内置计费", "安装会被计量并结算给你。你只写代码，不开账单。"], ["隔离 Runtime", "每个 Assistant 都在自己的容器中运行。没有共享状态，没有意外。"]],
    "发布你的第一个 Assistant",
    ["实时目录", "个 Assistant", "个 Assistant", "且持续增长", "Core", "Assistant 目录暂时不可用。", "重试"],
    "面向用户", "创建 Team，安装它需要的 Assistant，然后在聊天中与它交流——就像与人交流一样。",
    [["经审核，而非生成", "Assistant 是发布前经过审查的真实代码，不会临时编写。"], ["Team 相互隔离", "每个 Team 独立运行，拥有自己的 Assistant 和上下文。"], ["Self-hosted", "运行在你自己的基础设施上。你的数据留在你这里。"]],
  ],
  ja: [
    "一度書けば、ずっと売れる。· Shimpz", "レビュー済みの Assistant を一度公開し、すべての Shimpz Team に届けます。",
    "一度書けば、ずっと売れる。", "Assistant を作り、レビューを通過して公開する。インストールした Team から報酬を受け取れます。",
    "Spec を読む", "Assistant を見る",
    "開発者向け", "厳格な Spec に沿って開発し、人によるレビューを通過して公開。Assistant は Docker 内で分離実行され、管理するインフラはありません。",
    [["Spec とレビュー", "すべての Assistant が厳格な標準に従い、公開前に人の手で検証されます。"], ["組み込みの課金", "インストールは計測され、収益が支払われます。書くのはコードで、請求書ではありません。"], ["分離された Runtime", "各 Assistant は専用コンテナで実行されます。共有状態も想定外もありません。"]],
    "最初の Assistant を公開する",
    ["ライブカタログ", "件の Assistant", "件の Assistant", "、さらに増加中", "Core", "Assistant カタログは一時的に利用できません。", "再試行"],
    "ユーザー向け", "Team を作成し、必要な Assistant をインストールして、人と話すようにチャットで話しかけます。",
    [["生成ではなくレビュー済み", "Assistant は公開前に審査された実際のコードです。その場で書かれるものではありません。"], ["分離された Team", "各 Team は独自の Assistant とコンテキストを持ち、個別に実行されます。"], ["Self-hosted", "あなた自身のインフラで実行。データはあなたのもとに残ります。"]],
  ],
  ar: [
    "اكتبه مرة. وبعه إلى الأبد. · Shimpz", "أنشئ Assistant مراجعة وانشرها مرة واحدة لتصبح متاحة لكل Teams في Shimpz.",
    "اكتبه مرة. وبعه إلى الأبد.", "أنشئ Assistant واجتز المراجعة وانشرها. كل Team تثبّتها تدفع لك.",
    "اقرأ Spec", "تصفح Assistants",
    "للمطورين", "طوّر وفق Spec صارمة واجتز المراجعة اليدوية وانشر. تعمل Assistant معزولة داخل Docker — بلا بنية تحتية تديرها.",
    [["Spec ومراجعة", "تتبع كل Assistant معيارًا صارمًا وتُعتمد يدويًا قبل النشر."], ["فوترة مدمجة", "تُقاس عمليات التثبيت وتُدفع عوائدها. اكتب الكود، لا الفواتير."], ["Runtime معزول", "تعمل كل Assistant في حاويتها الخاصة. لا حالة مشتركة ولا مفاجآت."]],
    "انشر أول Assistant لك",
    ["الكتالوج المباشر", "Assistant", "Assistants", "وفي ازدياد", "Core", "كتالوج Assistants غير متاح مؤقتًا.", "أعد المحاولة"],
    "للمستخدمين", "أنشئ Team وثبّت Assistants التي تحتاجها وتحدث إليها في الدردشة — كما تتحدث مع الناس.",
    [["مراجعة لا مولّدة", "Assistants كود حقيقي يُفحص قبل النشر. لا يُكتب شيء لحظيًا."], ["Teams معزولة", "تعمل كل Team بصورة مستقلة مع Assistants وسياق خاصين بها."], ["Self-hosted", "تعمل على بنيتك التحتية. تبقى بياناتك لديك."]],
  ],
});

export function homepage(locale: Locale): HomepageContent {
  return CONTENT[locale];
}
