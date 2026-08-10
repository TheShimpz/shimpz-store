import type { Locale } from "$lib/locales";

type Profile = { title: string; body: string; detail: string };
type Concept = { title: string; body: string };
type InstitutionalContent = {
  seoTitle: string;
  seoDescription: string;
  eyebrow: string;
  title: string;
  lead: string;
  support: string;
  explore: string;
  documentation: string;
  profilesKicker: string;
  profilesTitle: string;
  profilesLead: string;
  profiles: [Profile, Profile];
  architectureKicker: string;
  architectureTitle: string;
  architectureLead: string;
  concepts: Concept[];
  publicationKicker: string;
  publicationTitle: string;
  publicationLead: string;
  flow: [Concept, Concept, Concept];
  openKicker: string;
  openTitle: string;
  openBody: string;
  github: string;
  finalTitle: string;
  finalBody: string;
};

const EN: InstitutionalContent = {
  seoTitle: "Shimpz — open-source Spaces for Teams and Assistants",
  seoDescription: "Shimpz is an open-source platform where isolated Teams use a shared Brain, explicit Services, and published Assistants in Local or Hosted Spaces.",
  eyebrow: "Open-source project · organized platform",
  title: "One Space. Clear boundaries. Teams that remain yours.",
  lead: "Shimpz is an open-source project and platform for running Teams with a shared reasoning Brain, explicitly authorized Services, and independently published Assistants.",
  support: "Use the Local profile on infrastructure you control or the Hosted profile through your Shimpz Account. The concepts and security boundaries remain the same.",
  explore: "Explore Assistants",
  documentation: "Read the documentation",
  profilesKicker: "One concept // two profiles",
  profilesTitle: "Local and Hosted speak the same product language.",
  profilesLead: "A Space is one concept. The profile changes who operates the infrastructure, not the meaning of Teams, Services, Brain, or Assistants.",
  profiles: [
    { title: "Local", body: "Run a Space on infrastructure you control and administer it through the local Shimpz Admin.", detail: "Your machine · your operational control" },
    { title: "Hosted", body: "Use your Shimpz Account to create and operate isolated Teams on the Hosted platform.", detail: "Account identity · managed infrastructure" },
  ],
  architectureKicker: "Product ontology // one mental model",
  architectureTitle: "Each name has one responsibility.",
  architectureLead: "The platform is organized around explicit ownership, isolation, and permission boundaries.",
  concepts: [
    { title: "Space", body: "The installation and administration boundary, with Local and Hosted profiles." },
    { title: "Services", body: "Shared Space capabilities exposed to isolated Team bindings through defined platform APIs." },
    { title: "Brain", body: "The shared reasoning runtime that answers as a Team and coordinates only capabilities allowed inside it." },
    { title: "Team", body: "The isolated authority for its Assistants, conversations, data, bindings, and lifecycle." },
    { title: "Assistant", body: "Independently published software whose declared Powers run inside an authorized Team through the standard path." },
  ],
  publicationKicker: "Assistant publication // one path",
  publicationTitle: "Developers → Store → Team.",
  publicationLead: "There are no private shortcuts or baked registries. Publication, discovery, authorization, verification, and lifecycle stay with their owning domains.",
  flow: [
    { title: "Developers", body: "Owns publication visibility and immutable source resolution." },
    { title: "Store", body: "Projects public discovery and sends the exact Assistant identity and source digest." },
    { title: "Team", body: "Owns authorization, verification, binding, installation, and lifecycle." },
  ],
  openKicker: "Open source // inspect the work",
  openTitle: "Built in public, documented as a system.",
  openBody: "Explore the Shimpz repositories and public documentation. The institutional site explains the product; the repositories preserve the implementation and its reviewable history.",
  github: "Open GitHub",
  finalTitle: "Choose the surface that matches what you want to do.",
  finalBody: "Discover an Assistant, inspect Services and Creators, open your Teams, or read the documentation. Every destination has a dedicated page and the same navigation.",
};

const CONTENT: Record<Locale, InstitutionalContent> = {
  en: EN,
  pt: {
    ...EN,
    seoTitle: "Shimpz — Spaces open source para Times e Assistants",
    seoDescription: "Shimpz é uma plataforma open source onde Times isolados usam um Brain compartilhado, Services explícitos e Assistants publicados em Spaces Local ou Hosted.",
    eyebrow: "Projeto open source · plataforma organizada",
    title: "Um Space. Limites claros. Times que continuam seus.",
    lead: "Shimpz é um projeto e uma plataforma open source para operar Times com um Brain de raciocínio compartilhado, Services autorizados explicitamente e Assistants publicados de forma independente.",
    support: "Use o perfil Local na infraestrutura que você controla ou o perfil Hosted pela sua Account Shimpz. Os conceitos e os limites de segurança continuam os mesmos.",
    explore: "Explorar Assistants", documentation: "Ler a documentação",
    profilesKicker: "Um conceito // dois perfis", profilesTitle: "Local e Hosted falam a mesma linguagem de produto.", profilesLead: "Space é um único conceito. O perfil muda quem opera a infraestrutura, não o significado de Teams, Services, Brain ou Assistants.",
    profiles: [
      { title: "Local", body: "Opere um Space na infraestrutura que você controla e administre-o pelo Shimpz Admin local.", detail: "Sua máquina · seu controle operacional" },
      { title: "Hosted", body: "Use sua Account Shimpz para criar e operar Times isolados na plataforma Hosted.", detail: "Identidade Account · infraestrutura gerenciada" },
    ],
    architectureKicker: "Ontologia do produto // um modelo mental", architectureTitle: "Cada nome tem uma responsabilidade.", architectureLead: "A plataforma é organizada em torno de limites explícitos de autoridade, isolamento e permissão.",
    concepts: [
      { title: "Space", body: "O limite de instalação e administração, com perfis Local e Hosted." },
      { title: "Services", body: "Capabilities compartilhadas do Space, expostas a bindings isolados de Times por APIs definidas da plataforma." },
      { title: "Brain", body: "O runtime de raciocínio compartilhado que responde como um Time e coordena somente capabilities permitidas nele." },
      { title: "Team", body: "A autoridade isolada de seus Assistants, conversas, dados, bindings e lifecycle." },
      { title: "Assistant", body: "Software publicado de forma independente cujos Powers declarados rodam em um Time autorizado pelo caminho padrão." },
    ],
    publicationKicker: "Publicação de Assistant // um caminho", publicationTitle: "Developers → Store → Team.", publicationLead: "Não existem atalhos privados nem registros embutidos. Publicação, descoberta, autorização, verificação e lifecycle permanecem com seus domínios responsáveis.",
    flow: [
      { title: "Developers", body: "Controla a visibilidade da publicação e a resolução imutável da fonte." },
      { title: "Store", body: "Projeta a descoberta pública e envia a identidade exata do Assistant e o digest da fonte." },
      { title: "Team", body: "Controla autorização, verificação, binding, instalação e lifecycle." },
    ],
    openKicker: "Open source // inspecione o trabalho", openTitle: "Construído em público, documentado como sistema.", openBody: "Explore os repositórios e a documentação pública do Shimpz. O site institucional explica o produto; os repositórios preservam a implementação e seu histórico revisável.", github: "Abrir GitHub",
    finalTitle: "Escolha a área que corresponde ao que você quer fazer.", finalBody: "Descubra um Assistant, consulte Services e Creators, abra seus Times ou leia a documentação. Cada destino tem uma página dedicada e a mesma navegação.",
  },
  es: {
    ...EN,
    seoTitle: "Shimpz — Spaces de código abierto para Teams y Assistants", seoDescription: "Shimpz es una plataforma de código abierto donde Teams aislados usan un Brain compartido, Services explícitos y Assistants publicados en Spaces Local o Hosted.", eyebrow: "Proyecto de código abierto · plataforma organizada", title: "Un Space. Límites claros. Teams que siguen siendo tuyos.", lead: "Shimpz es un proyecto y una plataforma de código abierto para operar Teams con un Brain de razonamiento compartido, Services autorizados explícitamente y Assistants publicados de forma independiente.", support: "Usa el perfil Local en la infraestructura que controlas o el perfil Hosted mediante tu Account de Shimpz. Los conceptos y límites de seguridad son los mismos.", explore: "Explorar Assistants", documentation: "Leer la documentación", profilesKicker: "Un concepto // dos perfiles", profilesTitle: "Local y Hosted hablan el mismo lenguaje de producto.", profilesLead: "Space es un único concepto. El perfil cambia quién opera la infraestructura, no el significado de Teams, Services, Brain o Assistants.", profiles: [{ title: "Local", body: "Ejecuta un Space en la infraestructura que controlas y adminístralo con Shimpz Admin local.", detail: "Tu máquina · tu control operativo" }, { title: "Hosted", body: "Usa tu Account de Shimpz para crear y operar Teams aislados en la plataforma Hosted.", detail: "Identidad Account · infraestructura gestionada" }], architectureKicker: "Ontología del producto // un modelo mental", architectureTitle: "Cada nombre tiene una responsabilidad.", architectureLead: "La plataforma se organiza con límites explícitos de autoridad, aislamiento y permisos.", concepts: [{ title: "Space", body: "El límite de instalación y administración, con perfiles Local y Hosted." }, { title: "Services", body: "Capacidades compartidas del Space expuestas a bindings aislados de Teams mediante APIs definidas." }, { title: "Brain", body: "El runtime de razonamiento compartido que responde como un Team y coordina solo capacidades permitidas." }, { title: "Team", body: "La autoridad aislada de sus Assistants, conversaciones, datos, bindings y ciclo de vida." }, { title: "Assistant", body: "Software publicado de forma independiente e instalado en un Team autorizado por la ruta estándar." }], publicationKicker: "Publicación de Assistant // una ruta", publicationTitle: "Developers → Store → Team.", publicationLead: "No hay atajos privados ni registros integrados. Cada dominio conserva su responsabilidad.", flow: [{ title: "Developers", body: "Controla la visibilidad y la resolución inmutable de la fuente." }, { title: "Store", body: "Proyecta el descubrimiento público y envía la identidad y el digest exactos." }, { title: "Team", body: "Controla autorización, verificación, binding, instalación y ciclo de vida." }], openKicker: "Código abierto // inspecciona el trabajo", openTitle: "Construido en público, documentado como sistema.", openBody: "Explora los repositorios y la documentación pública de Shimpz. El sitio explica el producto; los repositorios preservan la implementación y su historia revisable.", github: "Abrir GitHub", finalTitle: "Elige el área que corresponde a lo que quieres hacer.", finalBody: "Descubre un Assistant, consulta Services y Creators, abre tus Teams o lee la documentación. Cada destino tiene una página dedicada y la misma navegación.",
  },
  fr: {
    ...EN,
    seoTitle: "Shimpz — Spaces open source pour Teams et Assistants", seoDescription: "Shimpz est une plateforme open source où des Teams isolées utilisent un Brain partagé, des Services explicites et des Assistants publiés dans des Spaces Local ou Hosted.", eyebrow: "Projet open source · plateforme organisée", title: "Un Space. Des limites claires. Des Teams qui restent les vôtres.", lead: "Shimpz est un projet et une plateforme open source pour exécuter des Teams avec un Brain de raisonnement partagé, des Services explicitement autorisés et des Assistants publiés indépendamment.", support: "Utilisez le profil Local sur votre infrastructure ou le profil Hosted via votre Account Shimpz. Les concepts et limites de sécurité restent identiques.", explore: "Explorer les Assistants", documentation: "Lire la documentation", profilesKicker: "Un concept // deux profils", profilesTitle: "Local et Hosted parlent le même langage produit.", profilesLead: "Space est un concept unique. Le profil change l’opérateur de l’infrastructure, pas le sens des autres concepts.", profiles: [{ title: "Local", body: "Exécutez un Space sur l’infrastructure que vous contrôlez et administrez-le avec Shimpz Admin local.", detail: "Votre machine · votre contrôle" }, { title: "Hosted", body: "Utilisez votre Account Shimpz pour créer et exploiter des Teams isolées sur la plateforme Hosted.", detail: "Identité Account · infrastructure gérée" }], architectureKicker: "Ontologie produit // un modèle mental", architectureTitle: "Chaque nom a une responsabilité.", architectureLead: "La plateforme repose sur des limites explicites d’autorité, d’isolation et de permission.", concepts: [{ title: "Space", body: "La limite d’installation et d’administration, avec les profils Local et Hosted." }, { title: "Services", body: "Les capacités partagées du Space exposées aux bindings isolés des Teams par des API définies." }, { title: "Brain", body: "Le runtime de raisonnement partagé qui répond comme une Team et ne coordonne que les capacités autorisées." }, { title: "Team", body: "L’autorité isolée pour ses Assistants, conversations, données, bindings et cycle de vie." }, { title: "Assistant", body: "Un logiciel publié indépendamment et installé dans une Team autorisée par le parcours standard." }], publicationKicker: "Publication d’Assistant // un parcours", publicationTitle: "Developers → Store → Team.", publicationLead: "Aucun raccourci privé ni registre intégré. Chaque domaine conserve sa responsabilité.", flow: [{ title: "Developers", body: "Gère la visibilité de publication et la résolution immuable de la source." }, { title: "Store", body: "Projette la découverte publique et transmet l’identité et le digest exacts." }, { title: "Team", body: "Gère l’autorisation, la vérification, le binding, l’installation et le cycle de vie." }], openKicker: "Open source // inspectez le travail", openTitle: "Construit en public, documenté comme un système.", openBody: "Explorez les dépôts et la documentation publique Shimpz. Le site explique le produit ; les dépôts conservent l’implémentation et son historique vérifiable.", github: "Ouvrir GitHub", finalTitle: "Choisissez l’espace correspondant à votre objectif.", finalBody: "Découvrez un Assistant, consultez Services et Creators, ouvrez vos Teams ou lisez la documentation. Chaque destination a sa page et la même navigation.",
  },
  de: {
    ...EN,
    seoTitle: "Shimpz — Open-Source-Spaces für Teams und Assistants", seoDescription: "Shimpz ist eine Open-Source-Plattform, auf der isolierte Teams ein gemeinsames Brain, explizite Services und veröffentlichte Assistants in Local- oder Hosted-Spaces nutzen.", eyebrow: "Open-Source-Projekt · organisierte Plattform", title: "Ein Space. Klare Grenzen. Teams, die dir gehören.", lead: "Shimpz ist ein Open-Source-Projekt und eine Plattform für Teams mit gemeinsamem Reasoning-Brain, ausdrücklich autorisierten Services und unabhängig veröffentlichten Assistants.", support: "Nutze das Local-Profil auf eigener Infrastruktur oder Hosted über deinen Shimpz Account. Konzepte und Sicherheitsgrenzen bleiben gleich.", explore: "Assistants entdecken", documentation: "Dokumentation lesen", profilesKicker: "Ein Konzept // zwei Profile", profilesTitle: "Local und Hosted sprechen dieselbe Produktsprache.", profilesLead: "Space ist ein Konzept. Das Profil ändert den Betreiber der Infrastruktur, nicht die Bedeutung der Produktbegriffe.", profiles: [{ title: "Local", body: "Betreibe einen Space auf eigener Infrastruktur und verwalte ihn mit dem lokalen Shimpz Admin.", detail: "Deine Maschine · deine Kontrolle" }, { title: "Hosted", body: "Erstelle und betreibe isolierte Teams mit deinem Shimpz Account auf der Hosted-Plattform.", detail: "Account-Identität · verwaltete Infrastruktur" }], architectureKicker: "Produktontologie // ein mentales Modell", architectureTitle: "Jeder Name hat eine Verantwortung.", architectureLead: "Die Plattform folgt expliziten Autoritäts-, Isolations- und Berechtigungsgrenzen.", concepts: [{ title: "Space", body: "Die Installations- und Verwaltungsgrenze mit Local- und Hosted-Profilen." }, { title: "Services", body: "Gemeinsame Space-Fähigkeiten, die isolierten Team-Bindings über definierte APIs bereitgestellt werden." }, { title: "Brain", body: "Die gemeinsame Reasoning-Runtime, die als Team antwortet und nur erlaubte Fähigkeiten koordiniert." }, { title: "Team", body: "Die isolierte Autorität für Assistants, Gespräche, Daten, Bindings und Lebenszyklus." }, { title: "Assistant", body: "Unabhängig veröffentlichte Software, die über den Standardweg in ein autorisiertes Team installiert wird." }], publicationKicker: "Assistant-Veröffentlichung // ein Weg", publicationTitle: "Developers → Store → Team.", publicationLead: "Keine privaten Abkürzungen und keine eingebauten Register. Jede Domäne behält ihre Verantwortung.", flow: [{ title: "Developers", body: "Verantwortet Sichtbarkeit und unveränderliche Quellauflösung." }, { title: "Store", body: "Zeigt öffentliche Entdeckung und sendet exakte Identität und Digest." }, { title: "Team", body: "Verantwortet Autorisierung, Prüfung, Binding, Installation und Lebenszyklus." }], openKicker: "Open Source // Arbeit prüfen", openTitle: "Öffentlich gebaut, als System dokumentiert.", openBody: "Entdecke die Shimpz-Repositories und öffentliche Dokumentation. Die Website erklärt das Produkt; die Repositories bewahren Implementierung und prüfbare Historie.", github: "GitHub öffnen", finalTitle: "Wähle den Bereich für dein Ziel.", finalBody: "Entdecke Assistants, Services und Creators, öffne Teams oder lies die Dokumentation. Jedes Ziel hat eine eigene Seite und dieselbe Navigation.",
  },
  zh: {
    ...EN,
    seoTitle: "Shimpz — 面向 Teams 与 Assistants 的开源 Spaces", seoDescription: "Shimpz 是一个开源平台，隔离的 Teams 可在 Local 或 Hosted Spaces 中使用共享 Brain、明确的 Services 与已发布的 Assistants。", eyebrow: "开源项目 · 有序的平台", title: "一个 Space。清晰边界。始终属于你的 Teams。", lead: "Shimpz 是一个开源项目与平台，用于运行具有共享推理 Brain、明确授权 Services 和独立发布 Assistants 的 Teams。", support: "可在你控制的基础设施上使用 Local 配置，也可通过 Shimpz Account 使用 Hosted 配置。概念与安全边界保持一致。", explore: "浏览 Assistants", documentation: "阅读文档", profilesKicker: "一个概念 // 两种配置", profilesTitle: "Local 与 Hosted 使用同一种产品语言。", profilesLead: "Space 是一个概念。配置只改变基础设施的运营者，不改变产品概念的含义。", profiles: [{ title: "Local", body: "在你控制的基础设施上运行 Space，并通过本地 Shimpz Admin 管理。", detail: "你的机器 · 你的运营控制" }, { title: "Hosted", body: "使用 Shimpz Account 在 Hosted 平台创建并运行隔离的 Teams。", detail: "Account 身份 · 托管基础设施" }], architectureKicker: "产品本体 // 一个心智模型", architectureTitle: "每个名称只有一项职责。", architectureLead: "平台围绕明确的权限、隔离与授权边界组织。", concepts: [{ title: "Space", body: "安装与管理边界，包含 Local 与 Hosted 配置。" }, { title: "Services", body: "通过已定义平台 API 向隔离 Team bindings 提供的共享 Space 能力。" }, { title: "Brain", body: "代表 Team 回答、且只协调其中获准能力的共享推理 runtime。" }, { title: "Team", body: "其 Assistants、对话、数据、bindings 与生命周期的隔离权限主体。" }, { title: "Assistant", body: "独立发布并通过标准路径安装到已授权 Team 的软件。" }], publicationKicker: "Assistant 发布 // 一条路径", publicationTitle: "Developers → Store → Team。", publicationLead: "没有私有捷径或内置注册表。每个域都保留自身职责。", flow: [{ title: "Developers", body: "负责发布可见性与不可变源解析。" }, { title: "Store", body: "展示公开发现，并发送准确的身份与源摘要。" }, { title: "Team", body: "负责授权、验证、binding、安装与生命周期。" }], openKicker: "开源 // 检查工作", openTitle: "公开构建，按系统记录。", openBody: "浏览 Shimpz 仓库与公开文档。机构网站解释产品；仓库保留实现与可审查历史。", github: "打开 GitHub", finalTitle: "选择与你目标相符的区域。", finalBody: "发现 Assistant，查看 Services 与 Creators，打开 Teams 或阅读文档。每个目标都有专页与相同导航。",
  },
  ja: {
    ...EN,
    seoTitle: "Shimpz — Teams と Assistants のためのオープンソース Spaces", seoDescription: "Shimpz は、隔離された Teams が共有 Brain、明示的な Services、公開された Assistants を Local または Hosted Spaces で利用するオープンソースプラットフォームです。", eyebrow: "オープンソースプロジェクト · 整理されたプラットフォーム", title: "一つの Space。明確な境界。あなたのものであり続ける Teams。", lead: "Shimpz は、共有推論 Brain、明示的に許可された Services、独立して公開された Assistants で Teams を運用するオープンソースプロジェクト兼プラットフォームです。", support: "自分のインフラでは Local、Shimpz Account では Hosted を利用できます。概念とセキュリティ境界は同じです。", explore: "Assistants を見る", documentation: "ドキュメントを読む", profilesKicker: "一つの概念 // 二つのプロファイル", profilesTitle: "Local と Hosted は同じ製品言語を使います。", profilesLead: "Space は一つの概念です。プロファイルはインフラ運用者を変えますが、製品概念の意味は変えません。", profiles: [{ title: "Local", body: "自分が管理するインフラで Space を実行し、ローカル Shimpz Admin で管理します。", detail: "自分のマシン · 自分の運用管理" }, { title: "Hosted", body: "Shimpz Account で Hosted プラットフォーム上の隔離された Teams を作成・運用します。", detail: "Account ID · 管理されたインフラ" }], architectureKicker: "製品オントロジー // 一つのメンタルモデル", architectureTitle: "各名称には一つの責任があります。", architectureLead: "明示的な権限、隔離、許可の境界を中心に構成されています。", concepts: [{ title: "Space", body: "Local と Hosted を持つ、インストールと管理の境界。" }, { title: "Services", body: "定義済み API を通じて隔離された Team bindings に公開される共有 Space 能力。" }, { title: "Brain", body: "Team として回答し、許可された能力だけを調整する共有推論 runtime。" }, { title: "Team", body: "Assistants、会話、データ、bindings、ライフサイクルの隔離された権限主体。" }, { title: "Assistant", body: "独立公開され、標準経路で許可された Team にインストールされるソフトウェア。" }], publicationKicker: "Assistant 公開 // 一つの経路", publicationTitle: "Developers → Store → Team。", publicationLead: "非公開の近道や組み込みレジストリはありません。各ドメインが責任を保持します。", flow: [{ title: "Developers", body: "公開範囲と不変なソース解決を所有します。" }, { title: "Store", body: "公開検索を投影し、正確な ID とソースダイジェストを送ります。" }, { title: "Team", body: "許可、検証、binding、インストール、ライフサイクルを所有します。" }], openKicker: "オープンソース // 作業を確認", openTitle: "公開で構築し、システムとして文書化。", openBody: "Shimpz のリポジトリと公開文書をご覧ください。サイトは製品を説明し、リポジトリは実装とレビュー可能な履歴を保存します。", github: "GitHub を開く", finalTitle: "目的に合う領域を選んでください。", finalBody: "Assistant を探し、Services と Creators を確認し、Teams を開くか文書を読みます。すべて専用ページと同じナビゲーションがあります。",
  },
  ar: {
    ...EN,
    seoTitle: "Shimpz — Spaces مفتوحة المصدر لـ Teams وAssistants", seoDescription: "Shimpz منصة مفتوحة المصدر تستخدم فيها Teams المعزولة Brain مشتركًا وServices صريحة وAssistants منشورة ضمن Spaces محلية أو مستضافة.", eyebrow: "مشروع مفتوح المصدر · منصة منظّمة", title: "Space واحد. حدود واضحة. Teams تبقى ملكك.", lead: "Shimpz مشروع ومنصة مفتوحة المصدر لتشغيل Teams باستخدام Brain مشترك للاستدلال وServices مصرّح بها صراحة وAssistants منشورة بشكل مستقل.", support: "استخدم ملف Local على بنيتك التحتية أو ملف Hosted عبر Account في Shimpz. تبقى المفاهيم وحدود الأمان نفسها.", explore: "استكشف Assistants", documentation: "اقرأ الوثائق", profilesKicker: "مفهوم واحد // ملفان", profilesTitle: "يتحدث Local وHosted لغة المنتج نفسها.", profilesLead: "Space مفهوم واحد. يغيّر الملف مشغّل البنية التحتية، لا معنى مفاهيم المنتج.", profiles: [{ title: "Local", body: "شغّل Space على بنية تتحكم بها وأدره عبر Shimpz Admin المحلي.", detail: "جهازك · تحكمك التشغيلي" }, { title: "Hosted", body: "استخدم Account في Shimpz لإنشاء وتشغيل Teams معزولة على المنصة المستضافة.", detail: "هوية Account · بنية مُدارة" }], architectureKicker: "أنطولوجيا المنتج // نموذج ذهني واحد", architectureTitle: "لكل اسم مسؤولية واحدة.", architectureLead: "تُنظّم المنصة حول حدود صريحة للسلطة والعزل والصلاحيات.", concepts: [{ title: "Space", body: "حد التثبيت والإدارة مع ملفي Local وHosted." }, { title: "Services", body: "قدرات Space مشتركة تُعرض لارتباطات Teams المعزولة عبر واجهات محددة." }, { title: "Brain", body: "بيئة الاستدلال المشتركة التي تجيب باسم Team وتنسّق القدرات المسموح بها فقط." }, { title: "Team", body: "السلطة المعزولة على Assistants والمحادثات والبيانات والارتباطات ودورة الحياة." }, { title: "Assistant", body: "برنامج يُنشر مستقلًا ويُثبّت في Team مصرّح بها عبر المسار القياسي." }], publicationKicker: "نشر Assistant // مسار واحد", publicationTitle: "Developers → Store → Team.", publicationLead: "لا اختصارات خاصة ولا سجلات مدمجة. يحتفظ كل نطاق بمسؤوليته.", flow: [{ title: "Developers", body: "يملك رؤية النشر والحل غير القابل للتغيير للمصدر." }, { title: "Store", body: "يعرض الاكتشاف العام ويرسل الهوية وملخص المصدر الدقيقين." }, { title: "Team", body: "يملك التفويض والتحقق والارتباط والتثبيت ودورة الحياة." }], openKicker: "مفتوح المصدر // افحص العمل", openTitle: "مبني علنًا وموثّق كنظام.", openBody: "استكشف مستودعات Shimpz ووثائقها العامة. يشرح الموقع المنتج، وتحفظ المستودعات التنفيذ وتاريخه القابل للمراجعة.", github: "افتح GitHub", finalTitle: "اختر الوجهة المناسبة لما تريد فعله.", finalBody: "اكتشف Assistant أو راجع Services وCreators أو افتح Teams أو اقرأ الوثائق. لكل وجهة صفحة مخصصة والتنقل نفسه.",
  },
};

export function institutional(locale: Locale): InstitutionalContent {
  return CONTENT[locale];
}

const INSTALL: Record<Locale, Concept> = {
  en: { title: "Start on infrastructure you control.", body: "Review the installation guide, then run the canonical installer to create a Local Space and open its Shimpz Admin." },
  pt: { title: "Comece na infraestrutura que você controla.", body: "Revise o guia de instalação e execute o instalador canônico para criar um Space Local e abrir seu Shimpz Admin." },
  es: { title: "Empieza en la infraestructura que controlas.", body: "Revisa la guía y ejecuta el instalador canónico para crear un Space Local y abrir Shimpz Admin." },
  zh: { title: "从你控制的基础设施开始。", body: "阅读安装指南，然后运行标准安装程序来创建 Local Space 并打开 Shimpz Admin。" },
  fr: { title: "Commencez sur l’infrastructure que vous contrôlez.", body: "Consultez le guide, puis exécutez l’installateur canonique pour créer un Space Local et ouvrir Shimpz Admin." },
  de: { title: "Starte auf deiner eigenen Infrastruktur.", body: "Lies die Anleitung und führe den kanonischen Installer aus, um einen Local Space mit Shimpz Admin zu erstellen." },
  ja: { title: "自分が管理するインフラから始めましょう。", body: "ガイドを確認し、標準インストーラーを実行して Local Space を作成し、Shimpz Admin を開きます。" },
  ar: { title: "ابدأ على البنية التحتية التي تتحكم بها.", body: "راجع دليل التثبيت ثم شغّل المثبّت القياسي لإنشاء Local Space وفتح Shimpz Admin." },
};

const POWERS: Record<Locale, Concept> = {
  en: { title: "Declared Powers", body: "An Assistant exposes typed, named Powers. A Team authorizes what can run inside its boundary." },
  pt: { title: "Powers declarados", body: "Um Assistant expõe Powers tipados e nomeados. Um Time autoriza o que pode rodar dentro do seu limite." },
  es: { title: "Powers declarados", body: "Un Assistant expone Powers tipados y con nombre. Un Team autoriza lo que puede ejecutarse dentro de su límite." },
  zh: { title: "已声明的 Powers", body: "Assistant 公开有类型、有名称的 Powers。Team 决定哪些能力可在其边界内运行。" },
  fr: { title: "Powers déclarés", body: "Un Assistant expose des Powers typés et nommés. Une Team autorise ce qui peut s’exécuter dans sa limite." },
  de: { title: "Deklarierte Powers", body: "Ein Assistant stellt typisierte, benannte Powers bereit. Ein Team autorisiert, was innerhalb seiner Grenze laufen darf." },
  ja: { title: "宣言された Powers", body: "Assistant は型と名前を持つ Powers を公開します。Team は境界内で実行できるものを許可します。" },
  ar: { title: "Powers المعلنة", body: "يعرض Assistant قدرات Powers مسماة ومحددة النوع. وتصرّح Team بما يمكن تشغيله داخل حدودها." },
};

export function institutionalInstall(locale: Locale): Concept {
  return INSTALL[locale];
}

export function institutionalPowers(locale: Locale): Concept {
  return POWERS[locale];
}
