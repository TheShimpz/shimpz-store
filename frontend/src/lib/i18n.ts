// UI chrome uses English as the explicit fallback for incomplete operational translations.
import type { Locale } from "$lib/locales";

type Translation = { en: string } & Partial<Record<Locale, string>>;
type Dict = Record<string, Translation>;

const D: Dict = {
  home_copy: { en: "Copy", pt: "Copiar", es: "Copiar", zh: "复制", fr: "Copier", de: "Kopieren", ja: "コピー", ar: "نسخ" },
  home_copied: { en: "Copied", pt: "Copiado", es: "Copiado", zh: "已复制", fr: "Copié", de: "Kopiert", ja: "コピー済み", ar: "تم النسخ" },
  home_copy_failed: { en: "Try again", pt: "Tentar novamente", es: "Intentar de nuevo", zh: "重试", fr: "Réessayer", de: "Erneut versuchen", ja: "再試行", ar: "حاول مجددًا" },
  home_self_hosted: { en: "Self hosted", pt: "Auto-hospedado", es: "Autohospedado", zh: "自托管", fr: "Auto-hébergé", de: "Selbst gehostet", ja: "セルフホスト", ar: "مستضاف ذاتيًا" },
  home_sandboxed: { en: "Sandboxed", pt: "Em sandbox", es: "En sandbox", zh: "沙箱隔离", fr: "En sandbox", de: "In Sandbox", ja: "サンドボックス", ar: "ضمن بيئة معزولة" },
  home_open_source: { en: "Open-source components", pt: "Componentes open source", es: "Componentes de código abierto", zh: "开源组件", fr: "Composants open source", de: "Open-Source-Komponenten", ja: "オープンソース部品", ar: "مكونات مفتوحة المصدر" },
  home_privacy_line: { en: "No cookies, no trackers, no fingerprinting. Just a page.", pt: "Sem cookies, sem rastreadores, sem fingerprinting. Apenas uma página.", es: "Sin cookies, sin rastreadores, sin fingerprinting. Solo una página.", zh: "没有 Cookie，没有追踪器，没有浏览器指纹。只有一个页面。", fr: "Sans cookies, sans traceurs, sans fingerprinting. Juste une page.", de: "Keine Cookies, keine Tracker, kein Fingerprinting. Nur eine Seite.", ja: "Cookie もトラッカーもフィンガープリンティングもありません。ただのページです。", ar: "لا ملفات تعريف ارتباط، ولا أدوات تتبع، ولا بصمات رقمية. مجرد صفحة." },
  home_read_script: { en: "Read the script first", pt: "Leia o script primeiro", es: "Lee primero el script", zh: "先阅读脚本", fr: "Lisez d’abord le script", de: "Skript zuerst lesen", ja: "先にスクリプトを読む", ar: "اقرأ النص البرمجي أولًا" },
  nav_main: { en: "Main", pt: "Principal", es: "Principal", zh: "主导航", fr: "Principale", de: "Hauptnavigation", ja: "メイン", ar: "الرئيسية" },
  brand_home: { en: "Shimpz home", pt: "Início da Shimpz", es: "Inicio de Shimpz", zh: "Shimpz 首页", fr: "Accueil Shimpz", de: "Shimpz-Startseite", ja: "Shimpz ホーム", ar: "صفحة Shimpz الرئيسية" },
  nav_docs: { en: "Docs", pt: "Docs", es: "Docs", zh: "文档", fr: "Docs", de: "Doku", ja: "ドキュメント", ar: "الوثائق" },
  nav_open_source: { en: "Open source", pt: "Código aberto", es: "Código abierto", zh: "开源", fr: "Open source", de: "Open Source", ja: "オープンソース", ar: "مفتوح المصدر" },
  nav_about: { en: "About", pt: "Sobre", es: "Acerca de", zh: "关于", fr: "À propos", de: "Über uns", ja: "Shimpz について", ar: "حول Shimpz" },
  skip_content: { en: "Skip to content", pt: "Pular para o conteúdo", es: "Saltar al contenido", zh: "跳到内容", fr: "Aller au contenu", de: "Zum Inhalt springen", ja: "コンテンツへ移動", ar: "انتقل إلى المحتوى" },
  language: { en: "Language", pt: "Idioma", es: "Idioma", zh: "语言", fr: "Langue", de: "Sprache", ja: "言語", ar: "اللغة" },
  footer_links: { en: "Footer links", pt: "Links do rodapé", es: "Enlaces del pie", zh: "页脚链接", fr: "Liens de pied de page", de: "Fußzeilenlinks", ja: "フッターリンク", ar: "روابط التذييل" },
  footer_group_project: { en: "Project", pt: "Projeto", es: "Proyecto", zh: "项目", fr: "Projet", de: "Projekt", ja: "プロジェクト", ar: "المشروع" },
  footer_group_company: { en: "Company", pt: "Empresa", es: "Empresa", zh: "公司", fr: "Entreprise", de: "Unternehmen", ja: "会社", ar: "الشركة" },
  privacy: { en: "Privacy", pt: "Privacidade", es: "Privacidad", zh: "隐私", fr: "Confidentialité", de: "Datenschutz", ja: "プライバシー", ar: "الخصوصية" },
  terms: { en: "Terms", pt: "Termos", es: "Términos", zh: "条款", fr: "Conditions", de: "Bedingungen", ja: "利用規約", ar: "الشروط" },
  not_found_kicker: { en: "System // Route 404", pt: "Sistema // Rota 404", es: "Sistema // Ruta 404", zh: "系统 // 路径 404", fr: "Système // Route 404", de: "System // Route 404", ja: "システム // ルート 404", ar: "النظام // المسار 404" },
  not_found_title: { en: "This path went dark.", pt: "Este caminho saiu do ar.", es: "Esta ruta se quedó a oscuras.", zh: "这条路径已离线。", fr: "Cette route s’est éteinte.", de: "Dieser Pfad ist offline.", ja: "このルートはオフラインです。", ar: "هذا المسار غير متصل." },
  not_found_lead: {
    en: "The page you requested is not part of the current Shimpz surface. The system is online — choose a live destination.",
    pt: "A página que você procurou não faz parte da superfície atual da Shimpz. O sistema está online — escolha um destino ativo.",
    es: "La página que buscas no forma parte de la superficie actual de Shimpz. El sistema está en línea: elige un destino activo.",
    zh: "你请求的页面不在当前的 Shimpz 界面中。系统仍在线，请选择一个有效入口。",
    fr: "La page demandée ne fait pas partie de l’interface Shimpz actuelle. Le système est en ligne — choisissez une destination active.",
    de: "Die angeforderte Seite gehört nicht zur aktuellen Shimpz-Oberfläche. Das System ist online — wähle ein aktives Ziel.",
    ja: "リクエストされたページは現在の Shimpz にはありません。システムはオンラインです。有効な行き先を選んでください。",
    ar: "الصفحة التي طلبتها ليست جزءًا من واجهة Shimpz الحالية. النظام متصل — اختر وجهة متاحة.",
  },
  not_found_home: { en: "Return home", pt: "Voltar ao início", es: "Volver al inicio", zh: "返回首页", fr: "Retour à l’accueil", de: "Zur Startseite", ja: "ホームに戻る", ar: "العودة إلى الرئيسية" },
  not_found_assistants: { en: "Explore Assistants", pt: "Explorar Assistants", es: "Explorar Assistants", zh: "探索 Assistants", fr: "Explorer les Assistants", de: "Assistants entdecken", ja: "Assistants を見る", ar: "استكشاف Assistants" },
  assistants_title: { en: "Assistants", pt: "Assistants" },
  assistants_preview: { en: "Assistant Store // one catalog", pt: "Loja de Assistants // um catálogo" },
  assistants_lead: {
    en: "Team-native software that acts through declared Actions and collaborates through explicit permissions.",
    pt: "Software nativo de Time que atua por Actions declarados e colabora por permissões explícitas.",
  },
  assistants_free: { en: "Free", pt: "Grátis" },
  assistants_version: { en: "Version", pt: "Versão" },
  assistants_architectures: { en: "Architectures", pt: "Arquiteturas" },
  assistants_permissions: { en: "Security & access", pt: "Segurança e acesso" },
  assistants_action: { en: "Action", pt: "Action" },
  assistants_install_local: { en: "Install in local Admin", pt: "Instalar no Admin local" },
  assistants_uninstall_local: { en: "Uninstall", pt: "Desinstalar" },
  assistants_back_store: { en: "All Assistants", pt: "Todos os Assistants" },
  assistants_detail_actions: { en: "Declared Actions", pt: "Actions declarados" },
  assistants_actions_search: { en: "Search Actions", pt: "Buscar Actions" },
  assistants_actions_search_hint: {
    en: "Action, Integration or request",
    pt: "Action, integração ou solicitação",
  },
  assistants_actions_showing: { en: "Showing", pt: "Exibindo" },
  assistants_actions_of: { en: "of", pt: "de" },
  assistants_actions_no_matches: {
    en: "No Actions match this search.",
    pt: "Nenhum Action corresponde a esta busca.",
  },
  assistants_actions_show_more: { en: "Show more", pt: "Mostrar mais" },
  assistants_actions_show_all: { en: "Show all", pt: "Mostrar todos" },
  assistants_detail_published: { en: "Published Assistant", pt: "Assistant publicado" },
  assistants_detail_not_found: { en: "Assistant not found", pt: "Assistant não encontrado" },
  assistants_detail_not_found_help: {
    en: "This Assistant is not present in the current public catalog.",
    pt: "Este Assistant não está presente no catálogo público atual.",
  },
  assistants_catalog_loading: { en: "Loading Assistant…", pt: "Carregando Assistant…" },
  assistants_integrations: { en: "Integrations", pt: "Integrações" },
  assistants_human_requests: { en: "Human requests", pt: "Solicitações humanas" },
  assistants_allowed_hosts: { en: "Outbound hosts", pt: "Hosts de saída" },
  assistants_information: { en: "Information", pt: "Informações" },
  assistants_repository: { en: "Source", pt: "Código-fonte" },
  assistants_none: { en: "None declared", pt: "Nenhum declarado" },
  assistants_request_waiting: { en: "Contacting local Admin…", pt: "Contatando o Admin local…" },
  assistants_request_sent: {
    en: "Continue in the local Admin to confirm.",
    pt: "Continue no Admin local para confirmar.",
  },
  assistants_request_failed: {
    en: "The local Admin did not accept this request. Refresh and try again.",
    pt: "O Admin local não aceitou este pedido. Atualize e tente novamente.",
  },
  assistants_uninstall_request_sent: {
    en: "Continue in the local Admin to confirm uninstall.",
    pt: "Continue no Admin local para confirmar a desinstalação.",
  },
  assistants_uninstall_request_failed: {
    en: "The local Admin did not accept the uninstall request. Refresh and try again.",
    pt: "O Admin local não aceitou o pedido de desinstalação. Atualize e tente novamente.",
  },
  assistants_inventory_loading: {
    en: "Checking this Team…",
    pt: "Verificando este Time…",
  },
  assistants_inventory_unavailable: {
    en: "Local inventory unavailable",
    pt: "Inventário local indisponível",
  },
  assistants_catalog_unavailable: {
    en: "Assistant catalog unavailable",
    pt: "Catálogo de Assistants indisponível",
  },
  assistants_catalog_retry: {
    en: "Retry loading",
    pt: "Tentar carregar novamente",
  },
  assistants_admin_connecting: {
    en: "Connecting to local Admin…",
    pt: "Conectando ao Admin local…",
  },
  assistants_admin_connection_failed: {
    en: "The local Admin connection is not ready yet.",
    pt: "A conexão com o Admin local ainda não está pronta.",
  },
  assistants_admin_connection_retry: {
    en: "Retry connection",
    pt: "Tentar conexão novamente",
  },
};

export const tr = (key: string, l: Locale): string => D[key]?.[l] ?? D[key]?.en ?? key;
