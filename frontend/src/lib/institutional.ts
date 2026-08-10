import type { Locale } from "$lib/locales";

export type Concept = { title: string; body: string };
export type Profile = Concept & { detail: string };

export type InstitutionalContent = {
  seoTitle: string;
  seoDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  installKicker: string;
  installTitle: string;
  installBody: string;
  problemKicker: string;
  problemTitle: string;
  problemLead: string;
  modelKicker: string;
  modelTitle: string;
  modelLead: string;
  steps: [Concept, Concept, Concept];
  controlKicker: string;
  controlTitle: string;
  controlLead: string;
  controls: [Concept, Concept, Concept, Concept];
  securityLink: string;
  profilesKicker: string;
  profilesTitle: string;
  profilesLead: string;
  profiles: [Profile, Profile];
  openKicker: string;
  openTitle: string;
  openBody: string;
  openLink: string;
  github: string;
  assistantsLink: string;
};

export type InstitutionalPageContent = {
  seoTitle: string;
  seoDescription: string;
  kicker: string;
  title: string;
  lead: string;
  sections: Concept[];
  noteTitle: string;
  noteBody: string;
};

export type InstitutionalPage = "security" | "install" | "openSource" | "about";

const EN: InstitutionalContent = {
  seoTitle: "Shimpz — delegate real digital work without giving up control",
  seoDescription: "Talk to a Team, install programmed Assistants, authorize sensitive actions, and run Shimpz on infrastructure you control.",
  eyebrow: "Open-source organization · human authority",
  title: "The new AI standard you've been waiting for.",
  lead: "Talk to your Team. Install Assistants that give it programmed capabilities. Approve sensitive actions and inspect what happened.",
  installKicker: "Local Space // canonical installer",
  installTitle: "Start on infrastructure you control.",
  installBody: "Create a Local Space with the canonical installer. The same product language applies to the Hosted profile operated by Shimpz.",
  problemKicker: "A different boundary // less assembly, less improvisation",
  problemTitle: "Automation should not create more work.",
  problemLead: "Shimpz sits between workflow builders you must engineer and general agents you must continuously supervise.",
  modelKicker: "Shimpz // one useful mental model",
  modelTitle: "One conversation. Capabilities you choose.",
  modelLead: "The product model becomes visible only when it helps you decide what happens next.",
  steps: [
    { title: "Talk to a Team", body: "A Team keeps one isolated conversation, context, files, inference configuration, and workload boundary." },
    { title: "Install Assistants", body: "Each independently published Assistant gives the Team declared, reviewable capabilities." },
    { title: "Authorize the important parts", body: "When a Power needs human authority, execution pauses and asks before the consequential action." },
  ],
  controlKicker: "Control // part of execution",
  controlTitle: "Trust comes from visible mechanisms.",
  controlLead: "Shimpz names the boundary it enforces instead of asking you to believe an unsupported security adjective.",
  controls: [
    { title: "Scoped access", body: "Integrations request declared provider capabilities and scopes instead of a generic master key." },
    { title: "Human approval", body: "Consequential work can pause for attributable approval and the required assurance." },
    { title: "Isolated authority", body: "A Team keeps its own Assistants, state, files, bindings, credentials, and workload lifecycle." },
    { title: "Visible outcome", body: "Execution progress and terminal outcomes are projected without exposing prompts, payloads, or secrets." },
  ],
  securityLink: "Inspect the security model",
  profilesKicker: "One product // two profiles",
  profilesTitle: "Choose who operates the infrastructure.",
  profilesLead: "Local and Hosted are profiles of the same Space concept. Their product language stays consistent while their authority and topology differ where required.",
  profiles: [
    { title: "Local", body: "Run a Space on your Linux, Apple Silicon Mac, or Windows through WSL2.", detail: "Your infrastructure · your Supervisor" },
    { title: "Hosted", body: "Use the public Shimpz.com Space through an attributable Account.", detail: "Shimpz infrastructure · Account authority" },
  ],
  openKicker: "Open source // inspect the work",
  openTitle: "Built in public. Bounded when it runs.",
  openBody: "Shimpz is organized across independently versioned repositories with reviewable implementation history. Every Assistant, including Shimpz Cloudflare, uses the standard publication path.",
  openLink: "Understand what is open",
  github: "Open GitHub",
  assistantsLink: "Explore Assistants",
};

const CONTENT: Record<Locale, InstitutionalContent> = {
  en: EN,
  pt: {
    seoTitle: "Shimpz — delegue trabalho digital real sem abrir mão do controle",
    seoDescription: "Converse com um Time, instale Assistentes programados, autorize ações sensíveis e execute o Shimpz na infraestrutura que você controla.",
    eyebrow: "Organização de código aberto · autoridade humana",
    title: "O novo padrão de IA que você estava esperando.",
    lead: "Converse com seu Time. Instale Assistentes que oferecem capacidades programadas. Autorize ações sensíveis e inspecione o que aconteceu.",
    installKicker: "Space Local // instalador canônico",
    installTitle: "Comece na infraestrutura que você controla.",
    installBody: "Crie um Space Local com o instalador canônico. A mesma linguagem de produto se aplica ao perfil Hosted operado pela Shimpz.",
    problemKicker: "Um limite diferente // menos montagem, menos improviso",
    problemTitle: "Automatizar não deveria criar mais trabalho.",
    problemLead: "O Shimpz fica entre construtores de fluxos que você precisa programar e agentes genéricos que você precisa supervisionar o tempo todo.",
    modelKicker: "Shimpz // um modelo mental útil",
    modelTitle: "Uma conversa. Capacidades que você escolhe.",
    modelLead: "O modelo do produto aparece somente quando ajuda você a decidir o que acontece depois.",
    steps: [
      { title: "Converse com um Time", body: "Um Time mantém uma conversa, contexto, arquivos, configuração de inferência e limite de workload isolados." },
      { title: "Instale Assistentes", body: "Cada Assistente publicado de forma independente oferece capacidades declaradas e revisáveis ao Time." },
      { title: "Autorize o que importa", body: "Quando um Power precisa de autoridade humana, a execução pausa e pergunta antes da ação consequente." },
    ],
    controlKicker: "Controle // parte da execução",
    controlTitle: "Confiança nasce de mecanismos visíveis.",
    controlLead: "O Shimpz mostra o limite que impõe em vez de pedir que você acredite em um adjetivo de segurança sem prova.",
    controls: [
      { title: "Acesso restrito", body: "Integrações solicitam capacidades e escopos declarados do provedor, não uma chave mestra genérica." },
      { title: "Aprovação humana", body: "Trabalho consequente pode pausar para aprovação atribuível e para a garantia exigida." },
      { title: "Autoridade isolada", body: "Um Time mantém seus próprios Assistentes, estado, arquivos, bindings, credenciais e lifecycle de workloads." },
      { title: "Resultado visível", body: "O progresso e o resultado terminal aparecem sem expor prompts, payloads ou segredos." },
    ],
    securityLink: "Inspecionar o modelo de segurança",
    profilesKicker: "Um produto // dois perfis",
    profilesTitle: "Escolha quem opera a infraestrutura.",
    profilesLead: "Local e Hosted são perfis do mesmo conceito de Space. A linguagem permanece consistente; autoridade e topologia diferem quando necessário.",
    profiles: [
      { title: "Local", body: "Execute um Space no Linux, em um Mac Apple Silicon ou no Windows por WSL2.", detail: "Sua infraestrutura · seu Supervisor" },
      { title: "Hosted", body: "Use o Space público do Shimpz.com por meio de uma Account atribuível.", detail: "Infraestrutura Shimpz · autoridade da Account" },
    ],
    openKicker: "Código aberto // inspecione o trabalho",
    openTitle: "Construído em público. Limitado durante a execução.",
    openBody: "O Shimpz é organizado em repositórios versionados de forma independente, com histórico de implementação revisável. Todo Assistente, inclusive o Shimpz Cloudflare, segue o caminho padrão de publicação.",
    openLink: "Entender o que é aberto",
    github: "Abrir GitHub",
    assistantsLink: "Explorar Assistentes",
  },
  es: {
    seoTitle: "Shimpz — delega trabajo digital real sin perder el control",
    seoDescription: "Habla con un Team, instala Asistentes programados, autoriza acciones sensibles y ejecuta Shimpz en la infraestructura que controlas.",
    eyebrow: "Organización de código abierto · autoridad humana",
    title: "El nuevo estándar de IA que estabas esperando.",
    lead: "Habla con tu Team. Instala Asistentes que le aportan capacidades programadas. Autoriza acciones sensibles e inspecciona lo ocurrido.",
    installKicker: "Space Local // instalador canónico", installTitle: "Empieza en la infraestructura que controlas.", installBody: "Crea un Space Local con el instalador canónico. El mismo lenguaje de producto se aplica al perfil Hosted operado por Shimpz.",
    problemKicker: "Un límite diferente // menos montaje, menos improvisación", problemTitle: "Automatizar no debería crear más trabajo.", problemLead: "Shimpz se sitúa entre los constructores de flujos que debes programar y los agentes generales que debes supervisar continuamente.",
    modelKicker: "Shimpz // un modelo mental útil", modelTitle: "Una conversación. Capacidades que tú eliges.", modelLead: "El modelo del producto aparece solo cuando te ayuda a decidir qué sucede después.",
    steps: [{ title: "Habla con un Team", body: "Un Team mantiene aislados una conversación, contexto, archivos, configuración de inferencia y límite de trabajo." }, { title: "Instala Asistentes", body: "Cada Asistente publicado de forma independiente aporta capacidades declaradas y revisables al Team." }, { title: "Autoriza lo importante", body: "Cuando un Power necesita autoridad humana, la ejecución se pausa y pregunta antes de la acción relevante." }],
    controlKicker: "Control // parte de la ejecución", controlTitle: "La confianza nace de mecanismos visibles.", controlLead: "Shimpz muestra el límite que impone en vez de pedirte que creas en un adjetivo de seguridad sin pruebas.",
    controls: [{ title: "Acceso limitado", body: "Las Integraciones solicitan capacidades y alcances declarados del proveedor, no una llave maestra genérica." }, { title: "Aprobación humana", body: "El trabajo relevante puede pausarse para una aprobación atribuible y la garantía exigida." }, { title: "Autoridad aislada", body: "Un Team mantiene sus propios Asistentes, estado, archivos, bindings, credenciales y ciclo de vida." }, { title: "Resultado visible", body: "El progreso y los resultados finales se muestran sin exponer prompts, payloads ni secretos." }],
    securityLink: "Inspeccionar el modelo de seguridad",
    profilesKicker: "Un producto // dos perfiles", profilesTitle: "Elige quién opera la infraestructura.", profilesLead: "Local y Hosted son perfiles del mismo concepto Space. El lenguaje se mantiene; la autoridad y la topología difieren cuando es necesario.", profiles: [{ title: "Local", body: "Ejecuta un Space en Linux, un Mac con Apple Silicon o Windows mediante WSL2.", detail: "Tu infraestructura · tu Supervisor" }, { title: "Hosted", body: "Usa el Space público de Shimpz.com mediante una Account atribuible.", detail: "Infraestructura Shimpz · autoridad de Account" }],
    openKicker: "Código abierto // inspecciona el trabajo", openTitle: "Construido en público. Limitado al ejecutarse.", openBody: "Shimpz se organiza en repositorios versionados de forma independiente con un historial de implementación revisable. Todo Asistente, incluido Shimpz Cloudflare, sigue la ruta estándar de publicación.", openLink: "Entender qué es abierto", github: "Abrir GitHub",
    assistantsLink: "Explorar Asistentes",
  },
  fr: {
    seoTitle: "Shimpz — déléguez du travail numérique réel sans perdre le contrôle",
    seoDescription: "Parlez à une Team, installez des Assistants programmés, autorisez les actions sensibles et exécutez Shimpz sur votre infrastructure.",
    eyebrow: "Organisation open source · autorité humaine", title: "Le nouveau standard d’IA que vous attendiez.", lead: "Parlez à votre Team. Installez des Assistants qui lui apportent des capacités programmées. Autorisez les actions sensibles et inspectez le résultat.",
    installKicker: "Space Local // installateur canonique", installTitle: "Commencez sur l’infrastructure que vous contrôlez.", installBody: "Créez un Space Local avec l’installateur canonique. Le même langage produit s’applique au profil Hosted exploité par Shimpz.",
    problemKicker: "Une autre limite // moins d’assemblage, moins d’improvisation", problemTitle: "L’automatisation ne devrait pas créer plus de travail.", problemLead: "Shimpz se place entre les outils de workflow que vous devez construire et les agents généralistes que vous devez surveiller sans cesse.",
    modelKicker: "Shimpz // un modèle mental utile", modelTitle: "Une conversation. Les capacités que vous choisissez.", modelLead: "Le modèle du produit apparaît seulement lorsqu’il vous aide à décider de la suite.", steps: [{ title: "Parlez à une Team", body: "Une Team isole une conversation, son contexte, ses fichiers, sa configuration d’inférence et ses workloads." }, { title: "Installez des Assistants", body: "Chaque Assistant publié indépendamment apporte à la Team des capacités déclarées et vérifiables." }, { title: "Autorisez ce qui compte", body: "Lorsqu’un Power exige une autorité humaine, l’exécution se suspend et demande avant l’action importante." }],
    controlKicker: "Contrôle // dans l’exécution", controlTitle: "La confiance vient de mécanismes visibles.", controlLead: "Shimpz montre la limite qu’il impose plutôt que de vous demander de croire un adjectif de sécurité sans preuve.", controls: [{ title: "Accès limité", body: "Les Integrations demandent des capacités et scopes déclarés, pas une clé maîtresse générique." }, { title: "Approbation humaine", body: "Une action importante peut attendre une approbation attribuable et le niveau d’assurance requis." }, { title: "Autorité isolée", body: "Une Team conserve ses propres Assistants, états, fichiers, bindings, identifiants et cycle de vie." }, { title: "Résultat visible", body: "La progression et le résultat final apparaissent sans exposer prompts, payloads ou secrets." }], securityLink: "Inspecter le modèle de sécurité",
    profilesKicker: "Un produit // deux profils", profilesTitle: "Choisissez qui exploite l’infrastructure.", profilesLead: "Local et Hosted sont deux profils du même concept Space. Le langage reste cohérent; autorité et topologie diffèrent lorsque nécessaire.", profiles: [{ title: "Local", body: "Exécutez un Space sur Linux, un Mac Apple Silicon ou Windows via WSL2.", detail: "Votre infrastructure · votre Supervisor" }, { title: "Hosted", body: "Utilisez le Space public de Shimpz.com avec une Account attribuable.", detail: "Infrastructure Shimpz · autorité Account" }],
    openKicker: "Open source // inspectez le travail", openTitle: "Construit en public. Délimité à l’exécution.", openBody: "Shimpz est organisé en dépôts versionnés indépendamment avec un historique d’implémentation vérifiable. Chaque Assistant, y compris Shimpz Cloudflare, suit le parcours de publication standard.", openLink: "Comprendre ce qui est ouvert", github: "Ouvrir GitHub",
    assistantsLink: "Explorer les Assistants",
  },
  de: {
    seoTitle: "Shimpz — echte digitale Arbeit delegieren, ohne Kontrolle abzugeben", seoDescription: "Sprich mit einem Team, installiere programmierte Assistants, genehmige sensible Aktionen und betreibe Shimpz auf eigener Infrastruktur.", eyebrow: "Open-Source-Organisation · menschliche Autorität", title: "Der neue KI-Standard, auf den du gewartet hast.", lead: "Sprich mit deinem Team. Installiere Assistants mit programmierten Fähigkeiten. Genehmige sensible Aktionen und prüfe das Ergebnis.",
    installKicker: "Local Space // kanonischer Installer", installTitle: "Starte auf der Infrastruktur, die du kontrollierst.", installBody: "Erstelle mit dem kanonischen Installer einen Local Space. Dieselbe Produktsprache gilt für das von Shimpz betriebene Hosted-Profil.", problemKicker: "Eine andere Grenze // weniger Aufbau, weniger Improvisation", problemTitle: "Automatisierung sollte nicht mehr Arbeit erzeugen.", problemLead: "Shimpz liegt zwischen Workflow-Tools, die du konstruieren musst, und allgemeinen Agenten, die du ständig überwachen musst.",
    modelKicker: "Shimpz // ein nützliches Denkmodell", modelTitle: "Ein Gespräch. Fähigkeiten deiner Wahl.", modelLead: "Das Produktmodell wird erst sichtbar, wenn es dir bei der nächsten Entscheidung hilft.", steps: [{ title: "Sprich mit einem Team", body: "Ein Team hält Gespräch, Kontext, Dateien, Inferenzkonfiguration und Workload-Grenze isoliert." }, { title: "Installiere Assistants", body: "Jeder unabhängig veröffentlichte Assistant gibt dem Team deklarierte, prüfbare Fähigkeiten." }, { title: "Genehmige, was zählt", body: "Benötigt ein Power menschliche Autorität, pausiert die Ausführung vor der folgenreichen Aktion." }],
    controlKicker: "Kontrolle // Teil der Ausführung", controlTitle: "Vertrauen entsteht durch sichtbare Mechanismen.", controlLead: "Shimpz zeigt die erzwungene Grenze, statt unbelegte Sicherheitsadjektive zu verlangen.", controls: [{ title: "Begrenzter Zugriff", body: "Integrationen verlangen deklarierte Anbieterfähigkeiten und Scopes statt eines allgemeinen Hauptschlüssels." }, { title: "Menschliche Freigabe", body: "Folgenreiche Arbeit kann für eine zuordenbare Freigabe und die erforderliche Absicherung pausieren." }, { title: "Isolierte Autorität", body: "Ein Team behält eigene Assistants, Zustände, Dateien, Bindings, Zugangsdaten und Workload-Lebenszyklen." }, { title: "Sichtbares Ergebnis", body: "Fortschritt und Endergebnis werden gezeigt, ohne Prompts, Payloads oder Geheimnisse offenzulegen." }], securityLink: "Sicherheitsmodell prüfen",
    profilesKicker: "Ein Produkt // zwei Profile", profilesTitle: "Wähle, wer die Infrastruktur betreibt.", profilesLead: "Local und Hosted sind Profile desselben Space-Konzepts. Die Produktsprache bleibt gleich; Autorität und Topologie unterscheiden sich, wo nötig.", profiles: [{ title: "Local", body: "Betreibe einen Space unter Linux, auf einem Apple-Silicon-Mac oder unter Windows mit WSL2.", detail: "Deine Infrastruktur · dein Supervisor" }, { title: "Hosted", body: "Nutze den öffentlichen Shimpz.com Space über einen zuordenbaren Account.", detail: "Shimpz-Infrastruktur · Account-Autorität" }],
    openKicker: "Open Source // prüfe die Arbeit", openTitle: "Öffentlich entwickelt. Bei der Ausführung begrenzt.", openBody: "Shimpz ist in unabhängig versionierten Repositories mit prüfbarer Implementierungshistorie organisiert. Jeder Assistant, auch Shimpz Cloudflare, nutzt den Standardweg zur Veröffentlichung.", openLink: "Verstehen, was offen ist", github: "GitHub öffnen",
    assistantsLink: "Assistants entdecken",
  },
  zh: {
    seoTitle: "Shimpz — 委派真实的数字工作，同时保留控制权", seoDescription: "与 Team 对话，安装具有既定能力的 Assistant，授权敏感操作，并在你控制的基础设施上运行 Shimpz。", eyebrow: "开源组织 · 人类授权", title: "你一直在等待的全新 AI 标准。", lead: "与你的 Team 对话。安装为它提供既定能力的 Assistant。授权敏感操作，并检查实际发生了什么。",
    installKicker: "Local Space // 标准安装程序", installTitle: "从你控制的基础设施开始。", installBody: "使用标准安装程序创建 Local Space。由 Shimpz 运营的 Hosted 配置使用相同的产品语言。", problemKicker: "不同的边界 // 少搭建，少即兴", problemTitle: "自动化不应制造更多工作。", problemLead: "Shimpz 位于两者之间：一边是需要你设计的工作流工具，另一边是需要你持续监督的通用 Agent。",
    modelKicker: "Shimpz // 一个有用的心智模型", modelTitle: "一次对话。由你选择的能力。", modelLead: "只有在帮助你决定下一步时，产品模型才会出现。", steps: [{ title: "与 Team 对话", body: "Team 隔离保存对话、上下文、文件、推理配置和工作负载边界。" }, { title: "安装 Assistant", body: "每个独立发布的 Assistant 都为 Team 提供已声明且可审查的能力。" }, { title: "授权重要操作", body: "当 Power 需要人类授权时，执行会暂停，并在关键操作前询问你。" }],
    controlKicker: "控制 // 执行的一部分", controlTitle: "信任来自可见的机制。", controlLead: "Shimpz 展示实际执行的边界，而不是要求你相信没有证据的安全形容词。", controls: [{ title: "有限访问", body: "Integration 请求已声明的提供商能力和作用域，而不是通用主密钥。" }, { title: "人类批准", body: "关键工作可以暂停，等待可追溯的批准和所需的身份保证。" }, { title: "隔离授权", body: "Team 拥有自己的 Assistant、状态、文件、绑定、凭据和工作负载生命周期。" }, { title: "可见结果", body: "系统展示执行进度和最终结果，但不暴露提示、载荷或秘密。" }], securityLink: "查看安全模型",
    profilesKicker: "一个产品 // 两种配置", profilesTitle: "选择由谁运营基础设施。", profilesLead: "Local 和 Hosted 是同一 Space 概念的配置。产品语言保持一致；授权和拓扑在必要处不同。", profiles: [{ title: "Local", body: "在 Linux、Apple Silicon Mac 或通过 WSL2 的 Windows 上运行 Space。", detail: "你的基础设施 · 你的 Supervisor" }, { title: "Hosted", body: "通过可追溯的 Account 使用 Shimpz.com 公共 Space。", detail: "Shimpz 基础设施 · Account 授权" }],
    openKicker: "开源 // 检查工作", openTitle: "公开构建。运行时有明确边界。", openBody: "Shimpz 由独立版本化的仓库组成，保留可审查的实现历史。每个 Assistant，包括 Shimpz Cloudflare，都遵循标准发布路径。", openLink: "了解哪些内容是开放的", github: "打开 GitHub",
    assistantsLink: "浏览 Assistant",
  },
  ja: {
    seoTitle: "Shimpz — 制御を手放さずに、現実のデジタル作業を任せる", seoDescription: "Team と対話し、プログラムされた Assistant を導入し、重要な操作を承認して、管理するインフラで Shimpz を実行できます。", eyebrow: "オープンソース組織 · 人の権限", title: "あなたが待ち望んでいた、AI の新しいスタンダード。", lead: "Team と話し、プログラムされた能力を持つ Assistant を導入します。重要な操作を承認し、何が起きたか確認できます。",
    installKicker: "Local Space // 正規インストーラー", installTitle: "自分が管理するインフラから始める。", installBody: "正規インストーラーで Local Space を作成します。Shimpz が運用する Hosted プロファイルにも同じ製品言語が適用されます。", problemKicker: "異なる境界 // 組み立ても即興も少なく", problemTitle: "自動化が仕事を増やすべきではありません。", problemLead: "Shimpz は、自分で設計するワークフローツールと、常に監視が必要な汎用 Agent の間に位置します。",
    modelKicker: "Shimpz // 役立つメンタルモデル", modelTitle: "一つの対話。選べる能力。", modelLead: "製品モデルは、次の判断に役立つときだけ前面に現れます。", steps: [{ title: "Team と話す", body: "Team は対話、コンテキスト、ファイル、推論設定、ワークロード境界を分離します。" }, { title: "Assistant を導入する", body: "独立して公開された各 Assistant が、宣言済みで確認可能な能力を Team に与えます。" }, { title: "重要な部分を承認する", body: "Power に人の権限が必要な場合、実行は重要な操作の前で止まり、確認を求めます。" }],
    controlKicker: "制御 // 実行の一部", controlTitle: "信頼は見える仕組みから生まれる。", controlLead: "Shimpz は、根拠のない安全性の形容詞ではなく、実際に強制する境界を示します。", controls: [{ title: "限定されたアクセス", body: "Integration は汎用のマスターキーではなく、宣言済みのプロバイダー能力とスコープを要求します。" }, { title: "人による承認", body: "重要な処理は、追跡可能な承認と必要な保証を得るまで一時停止できます。" }, { title: "分離された権限", body: "Team ごとに Assistant、状態、ファイル、binding、認証情報、ワークロードのライフサイクルを保持します。" }, { title: "見える結果", body: "プロンプト、payload、秘密を公開せずに、進行状況と最終結果を示します。" }], securityLink: "セキュリティモデルを見る",
    profilesKicker: "一つの製品 // 二つのプロファイル", profilesTitle: "インフラを誰が運用するか選ぶ。", profilesLead: "Local と Hosted は同じ Space 概念のプロファイルです。製品言語は同じで、必要な箇所だけ権限と構成が異なります。", profiles: [{ title: "Local", body: "Linux、Apple Silicon Mac、または WSL2 上の Windows で Space を実行します。", detail: "自分のインフラ · 自分の Supervisor" }, { title: "Hosted", body: "追跡可能な Account で Shimpz.com の公開 Space を利用します。", detail: "Shimpz インフラ · Account 権限" }],
    openKicker: "オープンソース // 実装を確認", openTitle: "公開で構築。実行時は明確な境界。", openBody: "Shimpz は独立してバージョン管理されたリポジトリで構成され、確認可能な実装履歴を持ちます。Shimpz Cloudflare を含む全 Assistant が標準公開経路を使います。", openLink: "公開範囲を理解する", github: "GitHub を開く",
    assistantsLink: "Assistant を見る",
  },
  ar: {
    seoTitle: "Shimpz — فوّض العمل الرقمي الحقيقي دون التخلي عن التحكم", seoDescription: "تحدث مع Team وثبّت Assistants مبرمجة ووافق على الإجراءات الحساسة وشغّل Shimpz على بنيتك التحتية.", eyebrow: "منظمة مفتوحة المصدر · سلطة بشرية", title: "معيار الذكاء الاصطناعي الجديد الذي كنت تنتظره.", lead: "تحدث مع Team الخاصة بك. ثبّت Assistants تمنحها قدرات مبرمجة. وافق على الإجراءات الحساسة وافحص ما حدث.",
    installKicker: "Space محلية // المثبّت المعتمد", installTitle: "ابدأ على البنية التحتية التي تتحكم بها.", installBody: "أنشئ Space محلية بالمثبّت المعتمد. تنطبق لغة المنتج نفسها على ملف Hosted الذي تديره Shimpz.", problemKicker: "حد مختلف // تركيب أقل وارتجال أقل", problemTitle: "ينبغي ألا تنشئ الأتمتة مزيدًا من العمل.", problemLead: "تقع Shimpz بين أدوات سير العمل التي يجب أن تبنيها والوكلاء العامين الذين يجب أن تراقبهم باستمرار.",
    modelKicker: "Shimpz // نموذج ذهني مفيد", modelTitle: "محادثة واحدة. قدرات تختارها أنت.", modelLead: "لا يظهر نموذج المنتج إلا عندما يساعدك على اتخاذ القرار التالي.", steps: [{ title: "تحدث مع Team", body: "تعزل Team المحادثة والسياق والملفات وإعداد الاستدلال وحدود أعباء العمل." }, { title: "ثبّت Assistants", body: "تمنح كل Assistant منشورة بصورة مستقلة Team قدرات معلنة وقابلة للمراجعة." }, { title: "وافق على ما يهم", body: "عندما تحتاج Power إلى سلطة بشرية يتوقف التنفيذ ويسأل قبل الإجراء المؤثر." }],
    controlKicker: "التحكم // جزء من التنفيذ", controlTitle: "تأتي الثقة من آليات مرئية.", controlLead: "تعرض Shimpz الحد الذي تفرضه بدل مطالبتك بتصديق وصف أمني بلا دليل.", controls: [{ title: "وصول محدود", body: "تطلب Integrations قدرات ونطاقات معلنة من المزوّد بدل مفتاح رئيسي عام." }, { title: "موافقة بشرية", body: "يمكن أن يتوقف العمل المؤثر للحصول على موافقة منسوبة ومستوى الضمان المطلوب." }, { title: "سلطة معزولة", body: "تحتفظ Team بـ Assistants والحالة والملفات والروابط وبيانات الاعتماد ودورة حياة العمل الخاصة بها." }, { title: "نتيجة مرئية", body: "يظهر تقدم التنفيذ ونتيجته النهائية دون كشف prompts أو payloads أو الأسرار." }], securityLink: "افحص نموذج الأمان",
    profilesKicker: "منتج واحد // ملفان", profilesTitle: "اختر من يدير البنية التحتية.", profilesLead: "Local وHosted ملفان لمفهوم Space نفسه. تبقى لغة المنتج متسقة، وتختلف السلطة والبنية عند الحاجة.", profiles: [{ title: "Local", body: "شغّل Space على Linux أو Mac بمعالج Apple Silicon أو Windows عبر WSL2.", detail: "بنيتك التحتية · Supervisor الخاص بك" }, { title: "Hosted", body: "استخدم Space العامة على Shimpz.com من خلال Account منسوبة.", detail: "بنية Shimpz · سلطة Account" }],
    openKicker: "مفتوح المصدر // افحص العمل", openTitle: "يُبنى علنًا. ويعمل ضمن حدود.", openBody: "تُنظم Shimpz في مستودعات مستقلة الإصدارات مع تاريخ تنفيذ قابل للمراجعة. تستخدم كل Assistant، بما فيها Shimpz Cloudflare، مسار النشر القياسي.", openLink: "افهم ما هو مفتوح", github: "افتح GitHub",
    assistantsLink: "استكشف Assistants",
  },
};

const PAGE_CONTENT: Record<InstitutionalPage, Record<Locale, InstitutionalPageContent>> = {
  security: buildPages({
    en: ["Security // concrete controls", "Keep authority visible.", "Shimpz protects consequential work with explicit boundaries rather than an absolute security promise.", [
      ["Scoped Integration access", "Assistants declare the provider capabilities and scopes they need. Team binds encrypted provider tokens to the exact Team, Assistant, Integration, provider, scopes, and generation."],
      ["Human authority at the boundary", "A reviewed Power can pause for one Team-owned human request. Approval, denial, expiry, and authentication remain owned by the platform boundary, not by Assistant code."],
      ["Isolated execution", "Teams isolate workloads, files, bindings, credentials, networks, and lifecycle. The shared Brain gains none of an Assistant’s execution authority."],
      ["Audit without secret disclosure", "Security events record bounded principal metadata and outcomes. Tokens, keys, prompts, messages, file contents, and provider credentials are excluded."],
    ], "No absolute claim", "No system is absolutely secure. Shimpz publishes mechanisms and current limits, and fails closed when authority is unavailable or ambiguous."],
    pt: ["Segurança // controles concretos", "Mantenha a autoridade visível.", "O Shimpz protege trabalho consequente com limites explícitos, não com uma promessa absoluta de segurança.", [["Acesso restrito de Integration", "Assistentes declaram capacidades e escopos necessários. O Time vincula tokens criptografados ao Time, Assistente, Integration, provedor, escopos e geração exatos."], ["Autoridade humana no limite", "Um Power revisado pode pausar para uma solicitação humana do Time. Aprovação, recusa, expiração e autenticação pertencem à plataforma, não ao código do Assistente."], ["Execução isolada", "Times isolam workloads, arquivos, bindings, credenciais, redes e lifecycle. O Brain compartilhado não recebe a autoridade de execução de um Assistente."], ["Auditoria sem expor segredos", "Eventos de segurança registram metadados limitados do principal e resultados. Tokens, chaves, prompts, mensagens, arquivos e credenciais ficam de fora."]], "Nenhuma promessa absoluta", "Nenhum sistema é absolutamente seguro. O Shimpz publica mecanismos e limites atuais e falha de forma fechada quando a autoridade está indisponível ou ambígua."],
    es: ["Seguridad // controles concretos", "Mantén visible la autoridad.", "Shimpz protege el trabajo relevante con límites explícitos, no con una promesa absoluta de seguridad.", [["Acceso limitado de Integration", "Los Asistentes declaran las capacidades y alcances necesarios. El Team vincula tokens cifrados al Team, Asistente, Integration, proveedor, alcances y generación exactos."], ["Autoridad humana en el límite", "Un Power revisado puede pausarse para una solicitud humana del Team. Aprobación, rechazo, caducidad y autenticación pertenecen a la plataforma, no al código del Asistente."], ["Ejecución aislada", "Los Teams aíslan cargas, archivos, bindings, credenciales, redes y ciclo de vida. El Brain compartido no recibe la autoridad de ejecución de un Asistente."], ["Auditoría sin exponer secretos", "Los eventos registran metadatos limitados del principal y resultados. Tokens, claves, prompts, mensajes, archivos y credenciales quedan excluidos."]], "Sin promesas absolutas", "Ningún sistema es absolutamente seguro. Shimpz publica sus mecanismos y límites actuales y falla de forma cerrada cuando la autoridad no está disponible o es ambigua."],
    fr: ["Sécurité // contrôles concrets", "Gardez l’autorité visible.", "Shimpz protège les actions importantes par des limites explicites, pas par une promesse absolue de sécurité.", [["Accès Integration limité", "Les Assistants déclarent les capacités et scopes nécessaires. La Team lie les jetons chiffrés à la Team, l’Assistant, l’Integration, le fournisseur, les scopes et la génération exacts."], ["Autorité humaine à la limite", "Un Power vérifié peut attendre une demande humaine de la Team. Approbation, refus, expiration et authentification appartiennent à la plateforme, jamais au code Assistant."], ["Exécution isolée", "Les Teams isolent workloads, fichiers, bindings, identifiants, réseaux et cycle de vie. Le Brain partagé n’acquiert aucune autorité d’exécution d’un Assistant."], ["Audit sans divulguer les secrets", "Les événements consignent des métadonnées de principal limitées et les résultats. Jetons, clés, prompts, messages, fichiers et identifiants sont exclus."]], "Aucune promesse absolue", "Aucun système n’est absolument sûr. Shimpz publie ses mécanismes et limites actuelles et échoue fermé lorsque l’autorité est indisponible ou ambiguë."],
    de: ["Sicherheit // konkrete Kontrollen", "Autorität bleibt sichtbar.", "Shimpz schützt folgenreiche Arbeit mit expliziten Grenzen statt mit einem absoluten Sicherheitsversprechen.", [["Begrenzter Integration-Zugriff", "Assistants deklarieren benötigte Anbieterfähigkeiten und Scopes. Team bindet verschlüsselte Token an das exakte Team, den Assistant, die Integration, den Anbieter, die Scopes und Generation."], ["Menschliche Autorität an der Grenze", "Ein geprüftes Power kann für eine Team-eigene Anfrage pausieren. Freigabe, Ablehnung, Ablauf und Authentifizierung gehören der Plattform, nicht dem Assistant-Code."], ["Isolierte Ausführung", "Teams isolieren Workloads, Dateien, Bindings, Zugangsdaten, Netzwerke und Lebenszyklen. Das gemeinsame Brain erhält keine Ausführungsautorität eines Assistant."], ["Audit ohne Geheimnisse", "Ereignisse erfassen begrenzte Principal-Metadaten und Ergebnisse. Token, Schlüssel, Prompts, Nachrichten, Dateien und Anbieterzugänge bleiben ausgeschlossen."]], "Kein absolutes Versprechen", "Kein System ist absolut sicher. Shimpz veröffentlicht Mechanismen und aktuelle Grenzen und bleibt geschlossen, wenn Autorität fehlt oder mehrdeutig ist."],
    zh: ["安全 // 具体控制", "让授权保持可见。", "Shimpz 通过明确边界保护关键工作，而不是给出绝对安全承诺。", [["有限的 Integration 访问", "Assistant 声明所需的提供商能力和作用域。Team 将加密令牌绑定到准确的 Team、Assistant、Integration、提供商、作用域和代次。"], ["边界上的人类授权", "经过审查的 Power 可以暂停，等待 Team 所属的人类请求。批准、拒绝、过期和身份验证由平台边界负责，而不是 Assistant 代码。"], ["隔离执行", "Team 隔离工作负载、文件、绑定、凭据、网络和生命周期。共享 Brain 不会获得 Assistant 的执行权限。"], ["审计但不泄露秘密", "安全事件只记录有限的主体元数据和结果，不记录令牌、密钥、提示、消息、文件内容或提供商凭据。"]], "没有绝对承诺", "没有系统绝对安全。Shimpz 公布机制和当前限制；当授权不可用或含糊时，系统以关闭方式失败。"],
    ja: ["セキュリティ // 具体的な制御", "権限を見える状態に。", "Shimpz は絶対的な安全を約束するのではなく、明示的な境界で重要な作業を保護します。", [["限定された Integration アクセス", "Assistant は必要なプロバイダー能力とスコープを宣言します。Team は暗号化トークンを正確な Team、Assistant、Integration、プロバイダー、スコープ、世代に結び付けます。"], ["境界での人の権限", "確認済み Power は Team 所有の人への要求で一時停止できます。承認、拒否、期限切れ、認証は Assistant コードではなくプラットフォーム境界が管理します。"], ["分離された実行", "Team はワークロード、ファイル、binding、認証情報、ネットワーク、ライフサイクルを分離します。共有 Brain は Assistant の実行権限を得ません。"], ["秘密を出さない監査", "セキュリティイベントは限定された主体メタデータと結果だけを記録します。トークン、鍵、プロンプト、メッセージ、ファイル、認証情報は除外されます。"]], "絶対的な主張はしない", "絶対に安全なシステムはありません。Shimpz は仕組みと現在の限界を公開し、権限が不明または利用不能なら閉じた状態で失敗します。"],
    ar: ["الأمان // ضوابط ملموسة", "أبقِ السلطة مرئية.", "تحمي Shimpz العمل المؤثر بحدود صريحة، لا بوعد أمان مطلق.", [["وصول Integration محدود", "تعلن Assistants قدرات المزوّد ونطاقاته المطلوبة. تربط Team الرموز المشفرة بـ Team وAssistant وIntegration والمزوّد والنطاقات والجيل المحددة."], ["السلطة البشرية عند الحد", "يمكن أن تتوقف Power مراجعة لطلب بشري تملكه Team. الموافقة والرفض والانتهاء والمصادقة تملكها حدود المنصة، لا كود Assistant."], ["تنفيذ معزول", "تعزل Teams أعباء العمل والملفات والروابط وبيانات الاعتماد والشبكات ودورة الحياة. لا يحصل Brain المشترك على سلطة تنفيذ Assistant."], ["تدقيق بلا كشف الأسرار", "تسجل أحداث الأمان بيانات محدودة عن صاحب السلطة والنتائج. تُستبعد الرموز والمفاتيح وprompts والرسائل والملفات وبيانات المزوّد."]], "لا وعود مطلقة", "لا يوجد نظام آمن بصورة مطلقة. تنشر Shimpz الآليات والحدود الحالية وتفشل مغلقة عندما تكون السلطة غير متاحة أو ملتبسة."],
  }),
  install: buildPages({
    en: ["Local Space // install", "Run Shimpz on infrastructure you control.", "The canonical installer creates or reconciles one Local Space. Read the platform guide for the exact prerequisites before running it.", [["Linux", "Supported on Linux amd64 with a local Docker Engine and Docker Compose."], ["macOS", "Supported on Apple Silicon macOS with Docker Desktop."], ["Windows", "Supported on 64-bit Windows through Ubuntu on WSL2 with Docker Desktop integration."]], "One installer", "The command is served by install.shimpz.com. The public Docs remain the authority for current host requirements, setup, and troubleshooting."],
    pt: ["Space Local // instalação", "Execute o Shimpz na infraestrutura que você controla.", "O instalador canônico cria ou reconcilia um Space Local. Leia o guia da sua plataforma para conhecer os requisitos exatos antes de executá-lo.", [["Linux", "Suportado em Linux amd64 com Docker Engine local e Docker Compose."], ["macOS", "Suportado no macOS com Apple Silicon e Docker Desktop."], ["Windows", "Suportado no Windows 64 bits por Ubuntu no WSL2 com integração do Docker Desktop."]], "Um instalador", "O comando é servido por install.shimpz.com. A documentação pública é a autoridade para requisitos atuais, configuração e solução de problemas."],
    es: ["Space Local // instalación", "Ejecuta Shimpz en la infraestructura que controlas.", "El instalador canónico crea o reconcilia un Space Local. Lee la guía de tu plataforma para conocer los requisitos exactos antes de ejecutarlo.", [["Linux", "Compatible con Linux amd64, Docker Engine local y Docker Compose."], ["macOS", "Compatible con macOS en Apple Silicon y Docker Desktop."], ["Windows", "Compatible con Windows de 64 bits mediante Ubuntu en WSL2 e integración con Docker Desktop."]], "Un instalador", "El comando se sirve desde install.shimpz.com. La documentación pública es la autoridad sobre requisitos, configuración y resolución de problemas."],
    fr: ["Space Local // installation", "Exécutez Shimpz sur l’infrastructure que vous contrôlez.", "L’installateur canonique crée ou réconcilie un Space Local. Consultez le guide de votre plateforme avant de l’exécuter.", [["Linux", "Pris en charge sur Linux amd64 avec Docker Engine local et Docker Compose."], ["macOS", "Pris en charge sur macOS Apple Silicon avec Docker Desktop."], ["Windows", "Pris en charge sur Windows 64 bits via Ubuntu sous WSL2 avec l’intégration Docker Desktop."]], "Un installateur", "La commande est servie par install.shimpz.com. La documentation publique fait autorité pour les prérequis, la configuration et le dépannage."],
    de: ["Local Space // Installation", "Betreibe Shimpz auf deiner eigenen Infrastruktur.", "Der kanonische Installer erstellt oder gleicht einen Local Space ab. Lies vor dem Start die Anleitung für deine Plattform.", [["Linux", "Unterstützt auf Linux amd64 mit lokaler Docker Engine und Docker Compose."], ["macOS", "Unterstützt auf Apple-Silicon-macOS mit Docker Desktop."], ["Windows", "Unterstützt auf 64-Bit-Windows über Ubuntu unter WSL2 mit Docker-Desktop-Integration."]], "Ein Installer", "Der Befehl kommt von install.shimpz.com. Die öffentliche Dokumentation ist die Autorität für aktuelle Anforderungen, Einrichtung und Fehlerbehebung."],
    zh: ["Local Space // 安装", "在你控制的基础设施上运行 Shimpz。", "标准安装程序会创建或协调一个 Local Space。运行前请阅读对应平台指南中的准确要求。", [["Linux", "支持 Linux amd64、本地 Docker Engine 和 Docker Compose。"], ["macOS", "支持 Apple Silicon macOS 和 Docker Desktop。"], ["Windows", "支持 64 位 Windows，通过 WSL2 中的 Ubuntu 与 Docker Desktop 集成运行。"]], "一个安装程序", "命令由 install.shimpz.com 提供。公共文档是当前主机要求、设置和故障排查的权威来源。"],
    ja: ["Local Space // インストール", "自分が管理するインフラで Shimpz を実行する。", "正規インストーラーは Local Space を作成または調整します。実行前に各プラットフォームの正確な要件を確認してください。", [["Linux", "ローカル Docker Engine と Docker Compose を備えた Linux amd64 をサポートします。"], ["macOS", "Docker Desktop を備えた Apple Silicon macOS をサポートします。"], ["Windows", "Docker Desktop と連携した WSL2 上の Ubuntu で 64 ビット Windows をサポートします。"]], "一つのインストーラー", "コマンドは install.shimpz.com から提供されます。現在の要件、設定、トラブルシューティングは公開ドキュメントが正式な情報源です。"],
    ar: ["Space محلية // التثبيت", "شغّل Shimpz على البنية التحتية التي تتحكم بها.", "ينشئ المثبّت المعتمد Space محلية أو يطابق حالتها. اقرأ دليل منصتك لمعرفة المتطلبات الدقيقة قبل تشغيله.", [["Linux", "مدعوم على Linux amd64 مع Docker Engine محلي وDocker Compose."], ["macOS", "مدعوم على macOS بمعالج Apple Silicon مع Docker Desktop."], ["Windows", "مدعوم على Windows ‏64 بت عبر Ubuntu على WSL2 مع تكامل Docker Desktop."]], "مثبّت واحد", "يُقدَّم الأمر من install.shimpz.com. الوثائق العامة هي المرجع لمتطلبات المضيف والإعداد وحل المشكلات."],
  }),
  openSource: buildPages({
    en: ["Open source // inspect the work", "Open where trust needs evidence.", "Shimpz is an open-source organization. Public repositories expose the platform implementation and its reviewable history without granting any Assistant a privileged path.", [["Independent repositories", "Account, Admin, Assistants platform responsibilities, Brain, Browser, Developers, Docs, Services, Store, and Teams retain explicit source ownership."], ["One publication path", "Every Assistant, including Shimpz Cloudflare, is independently published through Developers, projected by Store, and authorized by Team."], ["Creator choice", "Platform openness does not claim that every Creator Assistant is open source. Each Assistant must state its own source availability honestly."]], "Inspect, do not assume", "The public website links to the exact repositories in scope. Open source never substitutes for runtime isolation, authority checks, or artifact verification."],
    pt: ["Código aberto // inspecione o trabalho", "Aberto onde a confiança precisa de evidência.", "O Shimpz é uma organização de código aberto. Repositórios públicos expõem a implementação da plataforma e seu histórico revisável sem conceder um caminho privilegiado a qualquer Assistente.", [["Repositórios independentes", "Account, Admin, responsabilidades de plataforma de Assistants, Brain, Browser, Developers, Docs, Services, Store e Teams mantêm ownership explícito do código."], ["Um caminho de publicação", "Todo Assistente, inclusive o Shimpz Cloudflare, é publicado independentemente por Developers, projetado pela Store e autorizado pelo Time."], ["Escolha do Creator", "A abertura da plataforma não afirma que todo Assistente de Creator é open source. Cada Assistente deve declarar honestamente a disponibilidade do próprio código."]], "Inspecione, não presuma", "O site público aponta para os repositórios exatos em escopo. Código aberto nunca substitui isolamento em runtime, verificação de autoridade ou de artefatos."],
    es: ["Código abierto // inspecciona el trabajo", "Abierto donde la confianza necesita pruebas.", "Shimpz es una organización de código abierto. Los repositorios públicos muestran la implementación y su historial revisable sin dar a ningún Asistente una ruta privilegiada.", [["Repositorios independientes", "Account, Admin, responsabilidades de Assistants, Brain, Browser, Developers, Docs, Services, Store y Teams mantienen ownership explícito del código."], ["Una ruta de publicación", "Cada Asistente, incluido Shimpz Cloudflare, se publica mediante Developers, se proyecta en Store y es autorizado por Team."], ["Elección del Creator", "La apertura de la plataforma no afirma que todo Asistente de un Creator sea open source. Cada Asistente declara honestamente la disponibilidad de su código."]], "Inspecciona, no supongas", "El sitio enlaza los repositorios exactos. El código abierto no sustituye el aislamiento, la autorización ni la verificación de artefactos."],
    fr: ["Open source // inspectez le travail", "Ouvert là où la confiance exige des preuves.", "Shimpz est une organisation open source. Les dépôts publics montrent l’implémentation et son historique vérifiable sans accorder de parcours privilégié à un Assistant.", [["Dépôts indépendants", "Account, Admin, responsabilités de plateforme Assistants, Brain, Browser, Developers, Docs, Services, Store et Teams conservent une ownership explicite du code."], ["Un parcours de publication", "Chaque Assistant, y compris Shimpz Cloudflare, est publié par Developers, projeté par Store et autorisé par Team."], ["Choix du Creator", "L’ouverture de la plateforme ne prétend pas que chaque Assistant de Creator est open source. Chacun déclare honnêtement la disponibilité de son code."]], "Inspectez, ne présumez pas", "Le site public relie les dépôts exacts. L’open source ne remplace jamais l’isolation, les contrôles d’autorité ou la vérification des artefacts."],
    de: ["Open Source // prüfe die Arbeit", "Offen, wo Vertrauen Belege braucht.", "Shimpz ist eine Open-Source-Organisation. Öffentliche Repositories zeigen Implementierung und prüfbare Historie, ohne einem Assistant einen Sonderweg zu geben.", [["Unabhängige Repositories", "Account, Admin, Assistant-Plattformaufgaben, Brain, Browser, Developers, Docs, Services, Store und Teams behalten eindeutige Quellverantwortung."], ["Ein Veröffentlichungsweg", "Jeder Assistant, auch Shimpz Cloudflare, wird durch Developers veröffentlicht, von Store dargestellt und von Team autorisiert."], ["Wahl des Creator", "Die offene Plattform bedeutet nicht, dass jeder Creator-Assistant Open Source ist. Jeder Assistant nennt seine Quellverfügbarkeit ehrlich."]], "Prüfen, nicht annehmen", "Die Website verlinkt die exakten Repositories. Open Source ersetzt nie Laufzeitisolation, Autoritätsprüfung oder Artefaktverifikation."],
    zh: ["开源 // 检查工作", "在信任需要证据的地方保持开放。", "Shimpz 是一个开源组织。公共仓库展示平台实现和可审查历史，同时不会为任何 Assistant 提供特权路径。", [["独立仓库", "Account、Admin、Assistant 平台职责、Brain、Browser、Developers、Docs、Services、Store 和 Teams 都有明确的源码归属。"], ["一条发布路径", "每个 Assistant，包括 Shimpz Cloudflare，都通过 Developers 独立发布，由 Store 展示，并由 Team 授权。"], ["Creator 的选择", "平台开放不代表每个 Creator Assistant 都是开源的。每个 Assistant 必须如实说明源码可用性。"]], "检查，而不是假设", "公共网站链接到准确范围内的仓库。开源不能替代运行时隔离、授权检查或制品验证。"],
    ja: ["オープンソース // 実装を確認", "信頼に証拠が必要な場所を公開する。", "Shimpz はオープンソース組織です。公開リポジトリで実装と確認可能な履歴を示しつつ、どの Assistant にも特別な経路を与えません。", [["独立したリポジトリ", "Account、Admin、Assistant プラットフォーム責任、Brain、Browser、Developers、Docs、Services、Store、Teams は明示的なソース所有を保ちます。"], ["一つの公開経路", "Shimpz Cloudflare を含む全 Assistant は Developers から独立公開され、Store に表示され、Team によって承認されます。"], ["Creator の選択", "プラットフォームが開かれていても、すべての Creator Assistant がオープンソースとは限りません。各 Assistant がソース公開状況を正直に示します。"]], "推測せず確認する", "公開サイトは対象となる正確なリポジトリにリンクします。オープンソースは実行時分離、権限確認、制品検証の代わりにはなりません。"],
    ar: ["مفتوح المصدر // افحص العمل", "مفتوح حيث تحتاج الثقة إلى دليل.", "Shimpz منظمة مفتوحة المصدر. تعرض المستودعات العامة تنفيذ المنصة وتاريخه القابل للمراجعة دون منح أي Assistant مسارًا مميزًا.", [["مستودعات مستقلة", "تحتفظ Account وAdmin ومسؤوليات منصة Assistants وBrain وBrowser وDevelopers وDocs وServices وStore وTeams بملكية مصدر واضحة."], ["مسار نشر واحد", "تُنشر كل Assistant، بما فيها Shimpz Cloudflare، بصورة مستقلة عبر Developers وتعرضها Store وتصرح بها Team."], ["اختيار Creator", "انفتاح المنصة لا يعني أن كل Assistant ينشئها Creator مفتوحة المصدر. تصف كل Assistant توفر مصدرها بصدق."]], "افحص ولا تفترض", "يربط الموقع بالمستودعات الدقيقة ضمن النطاق. لا يحل المصدر المفتوح محل عزل التشغيل أو فحوص السلطة أو التحقق من القطع."],
  }),
  about: buildPages({
    en: ["About // why Shimpz exists", "Built for presence, not for more screen time.", "Shimpz is an open-source organization founded by Juliano Amaral Gouveia from a working personal system and a simple need: useful digital work should not keep a founder attached to a notebook.", [["Sworder and Neo", "The first system connected Meta Ads, Cloudflare, and a server to an AI experience administered through Telegram. It performed useful work, but remained bespoke, reactive, and expensive to operate safely."], ["A human reason", "While Juliano’s wife was pregnant, freedom from the notebook meant something concrete: more presence with his family without abandoning responsibility for the work."], ["The Shimpz thesis", "Reasoning should coordinate bounded, reusable software instead of inventing every implementation again. Humans keep authority over access and consequential decisions."]], "An organization and a project", "Shimpz presents the company and the open-source work with one voice: precise about what exists, explicit about what is still future, and organized so the product can outlive one session or one person’s memory."],
    pt: ["Sobre // por que o Shimpz existe", "Construído para presença, não para mais tempo de tela.", "O Shimpz é uma organização de código aberto fundada por Juliano Amaral Gouveia a partir de um sistema pessoal funcional e de uma necessidade simples: trabalho digital útil não deveria prender um fundador ao notebook.", [["Sworder e Neo", "O primeiro sistema conectava Meta Ads, Cloudflare e um servidor a uma experiência de IA administrada pelo Telegram. Realizava trabalho útil, mas continuava artesanal, reativo e caro de operar com segurança."], ["Uma razão humana", "Enquanto a esposa de Juliano estava grávida, liberdade do notebook significava algo concreto: estar mais presente com a família sem abandonar a responsabilidade pelo trabalho."], ["A tese do Shimpz", "O raciocínio deve coordenar software limitado e reutilizável em vez de inventar cada implementação novamente. Humanos mantêm autoridade sobre acessos e decisões consequentes."]], "Uma organização e um projeto", "O Shimpz apresenta a empresa e o trabalho open source com uma voz: preciso sobre o que existe, explícito sobre o que ainda é futuro e organizado para que o produto sobreviva a uma sessão ou à memória de uma pessoa."],
    es: ["Acerca de // por qué existe Shimpz", "Creado para estar presente, no para pasar más tiempo frente a una pantalla.", "Shimpz es una organización de código abierto fundada por Juliano Amaral Gouveia a partir de un sistema personal funcional y una necesidad sencilla: el trabajo digital útil no debería atar a un fundador a su portátil.", [["Sworder y Neo", "El primer sistema conectó Meta Ads, Cloudflare y un servidor con una experiencia de IA administrada por Telegram. Hacía trabajo útil, pero seguía siendo artesanal, reactivo y costoso de operar de forma segura."], ["Una razón humana", "Mientras la esposa de Juliano estaba embarazada, liberarse del portátil significaba algo concreto: estar más presente con su familia sin abandonar la responsabilidad por el trabajo."], ["La tesis de Shimpz", "El razonamiento debe coordinar software limitado y reutilizable en vez de inventar cada implementación de nuevo. Los humanos conservan la autoridad sobre accesos y decisiones relevantes."]], "Una organización y un proyecto", "Shimpz presenta la empresa y el trabajo open source con una sola voz: precisa sobre lo que existe, explícita sobre el futuro y organizada para superar una sesión o la memoria de una persona."],
    fr: ["À propos // pourquoi Shimpz existe", "Conçu pour être présent, pas pour ajouter du temps d’écran.", "Shimpz est une organisation open source fondée par Juliano Amaral Gouveia à partir d’un système personnel fonctionnel et d’un besoin simple : le travail numérique utile ne devrait pas attacher un fondateur à son ordinateur.", [["Sworder et Neo", "Le premier système reliait Meta Ads, Cloudflare et un serveur à une expérience d’IA administrée via Telegram. Il produisait du travail utile, mais restait sur mesure, réactif et coûteux à exploiter de façon sûre."], ["Une raison humaine", "Pendant la grossesse de l’épouse de Juliano, se libérer de l’ordinateur signifiait être plus présent auprès de sa famille sans abandonner la responsabilité du travail."], ["La thèse Shimpz", "Le raisonnement doit coordonner des logiciels limités et réutilisables plutôt que réinventer chaque implémentation. Les humains gardent l’autorité sur les accès et décisions importantes."]], "Une organisation et un projet", "Shimpz présente l’entreprise et le travail open source d’une seule voix : précise sur l’existant, explicite sur l’avenir et organisée pour dépasser une session ou la mémoire d’une personne."],
    de: ["Über uns // warum Shimpz existiert", "Für Präsenz gebaut, nicht für mehr Bildschirmzeit.", "Shimpz ist eine von Juliano Amaral Gouveia gegründete Open-Source-Organisation. Ausgangspunkt waren ein funktionierendes persönliches System und ein einfacher Bedarf: Nützliche digitale Arbeit sollte einen Gründer nicht an sein Notebook binden.", [["Sworder und Neo", "Das erste System verband Meta Ads, Cloudflare und einen Server mit einer über Telegram verwalteten KI-Erfahrung. Es erledigte echte Arbeit, blieb aber individuell, reaktiv und teuer im sicheren Betrieb."], ["Ein menschlicher Grund", "Während Julianes Frau schwanger war, bedeutete Freiheit vom Notebook etwas Konkretes: mehr Präsenz bei der Familie, ohne Verantwortung für die Arbeit abzugeben."], ["Die Shimpz-These", "Reasoning soll begrenzte, wiederverwendbare Software koordinieren, statt jede Implementierung neu zu erfinden. Menschen behalten Autorität über Zugriffe und folgenreiche Entscheidungen."]], "Organisation und Projekt", "Shimpz spricht für Unternehmen und Open-Source-Arbeit mit einer Stimme: präzise über das Bestehende, deutlich über die Zukunft und so organisiert, dass das Produkt mehr als eine Sitzung oder Erinnerung überdauert."],
    zh: ["关于 // Shimpz 为何存在", "为了真正陪伴，而不是增加屏幕时间。", "Shimpz 是 Juliano Amaral Gouveia 创立的开源组织。它源自一个实际运行的个人系统和一个简单需求：有用的数字工作不应把创始人绑在笔记本电脑前。", [["Sworder 与 Neo", "最初的系统把 Meta Ads、Cloudflare 和服务器连接到通过 Telegram 管理的 AI 体验。它能完成真实工作，但仍是定制的、被动的，并且难以安全地规模化运营。"], ["一个人的理由", "Juliano 的妻子怀孕期间，摆脱笔记本电脑有了具体含义：在不放弃工作责任的同时，更多地陪伴家人。"], ["Shimpz 的主张", "推理应协调有边界、可复用的软件，而不是每次重新发明实现。人类保留对访问权限和关键决策的授权。"]], "一个组织，也是一个项目", "Shimpz 以同一种声音介绍公司和开源工作：准确说明已有内容，明确标记未来方向，并通过组织化让产品不依赖一次会话或一个人的记忆。"],
    ja: ["Shimpz について // なぜ存在するのか", "画面を見る時間ではなく、大切な場にいるために。", "Shimpz は Juliano Amaral Gouveia が、実際に動く個人システムと一つの必要性から設立したオープンソース組織です。有用なデジタル作業のために、創業者がノート PC に縛られるべきではありません。", [["Sworder と Neo", "最初のシステムは Meta Ads、Cloudflare、サーバーを Telegram で管理する AI 体験につなぎました。実際の仕事はできましたが、個別構築で反応的、かつ安全な運用コストが高いものでした。"], ["人としての理由", "Juliano の妻が妊娠していた時期、ノート PC からの自由には具体的な意味がありました。仕事の責任を放棄せず、家族と過ごす時間を増やすことです。"], ["Shimpz の考え", "推論は実装を毎回発明するのではなく、境界のある再利用可能なソフトウェアを調整すべきです。アクセスと重要な判断の権限は人が持ちます。"]], "組織でありプロジェクト", "Shimpz は会社とオープンソース活動を一つの声で伝えます。存在するものを正確に、未来を明示し、一度の会話や一人の記憶を超えて続くよう整理します。"],
    ar: ["حول Shimpz // لماذا وُجدت", "بُنيت للحضور، لا لمزيد من وقت الشاشة.", "Shimpz منظمة مفتوحة المصدر أسسها Juliano Amaral Gouveia انطلاقًا من نظام شخصي عامل وحاجة بسيطة: لا ينبغي للعمل الرقمي المفيد أن يربط المؤسس بحاسوبه المحمول.", [["Sworder وNeo", "ربط النظام الأول Meta Ads وCloudflare وخادمًا بتجربة ذكاء اصطناعي تُدار عبر Telegram. أنجز عملًا مفيدًا، لكنه بقي مخصصًا وتفاعليًا ومكلفًا للتشغيل الآمن."], ["سبب إنساني", "أثناء حمل زوجة Juliano، كان للتحرر من الحاسوب معنى ملموس: حضور أكبر مع العائلة دون التخلي عن مسؤولية العمل."], ["أطروحة Shimpz", "ينبغي للاستدلال أن ينسق برمجيات محدودة وقابلة لإعادة الاستخدام بدل اختراع كل تنفيذ من جديد. يحتفظ البشر بالسلطة على الوصول والقرارات المؤثرة."]], "منظمة ومشروع", "تقدم Shimpz الشركة والعمل مفتوح المصدر بصوت واحد: دقيق بشأن الموجود، وصريح بشأن المستقبل، ومنظم كي يتجاوز المنتج جلسة واحدة أو ذاكرة شخص واحد."],
  }),
};

type PageTuple = [string, string, string, [string, string][], string, string];

function buildPages(input: Record<Locale, PageTuple>): Record<Locale, InstitutionalPageContent> {
  return Object.fromEntries(Object.entries(input).map(([locale, [kicker, title, lead, sections, noteTitle, noteBody]]) => [
    locale,
    {
      seoTitle: `${title} · Shimpz`,
      seoDescription: lead,
      kicker,
      title,
      lead,
      sections: sections.map(([sectionTitle, body]) => ({ title: sectionTitle, body })),
      noteTitle,
      noteBody,
    },
  ])) as Record<Locale, InstitutionalPageContent>;
}

export function institutional(locale: Locale): InstitutionalContent {
  return CONTENT[locale];
}

export function institutionalPage(page: InstitutionalPage, locale: Locale): InstitutionalPageContent {
  return PAGE_CONTENT[page][locale];
}
