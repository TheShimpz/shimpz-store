import { t, type I18n, type Locale } from "./catalog.ts";

export type HomepageRequestGroup = "approval" | "input" | "auth";

export type HomepageRequest = {
  kind: string;
  label: I18n;
  signature: string;
  group: HomepageRequestGroup;
};

type PreviewCopy = {
  description: string;
  fieldLabel: string;
  actionSummary: string;
  placeholder: string;
  optionOne: string;
  optionTwo: string;
};

const PREVIEW_COPY: Record<Locale, PreviewCopy> = {
  en: {
    description: "I paused this Action until you answer this request.",
    fieldLabel: "Requested value",
    actionSummary: "Change one reviewed DNS record.",
    placeholder: "Enter the reviewed value",
    optionOne: "Use the current domain",
    optionTwo: "Create a new domain",
  },
  pt: {
    description: "Eu pausei este Action até você responder a esta solicitação.",
    fieldLabel: "Valor solicitado",
    actionSummary: "Alterar um registro DNS revisado.",
    placeholder: "Digite o valor revisado",
    optionOne: "Usar o domínio atual",
    optionTwo: "Criar um novo domínio",
  },
  es: {
    description: "He pausado este Action hasta que respondas a esta solicitud.",
    fieldLabel: "Valor solicitado",
    actionSummary: "Cambiar un registro DNS revisado.",
    placeholder: "Introduce el valor revisado",
    optionOne: "Usar el dominio actual",
    optionTwo: "Crear un dominio nuevo",
  },
  zh: {
    description: "我已暂停此 Action，等待你回应这项请求。",
    fieldLabel: "请求的值",
    actionSummary: "更改一条已审核的 DNS 记录。",
    placeholder: "输入已审核的值",
    optionOne: "使用当前域名",
    optionTwo: "创建新域名",
  },
  fr: {
    description: "J’ai suspendu ce Action jusqu’à votre réponse à cette demande.",
    fieldLabel: "Valeur demandée",
    actionSummary: "Modifier un enregistrement DNS vérifié.",
    placeholder: "Saisissez la valeur vérifiée",
    optionOne: "Utiliser le domaine actuel",
    optionTwo: "Créer un nouveau domaine",
  },
  de: {
    description: "Ich habe diesen Action angehalten, bis du diese Anfrage beantwortest.",
    fieldLabel: "Angeforderter Wert",
    actionSummary: "Einen geprüften DNS-Eintrag ändern.",
    placeholder: "Geprüften Wert eingeben",
    optionOne: "Aktuelle Domain verwenden",
    optionTwo: "Neue Domain erstellen",
  },
  ja: {
    description: "このリクエストに回答するまで、Action を一時停止しています。",
    fieldLabel: "要求された値",
    actionSummary: "確認済みの DNS レコードを変更する。",
    placeholder: "確認済みの値を入力",
    optionOne: "現在のドメインを使用",
    optionTwo: "新しいドメインを作成",
  },
  ar: {
    description: "أوقفت هذا الـ Action مؤقتًا حتى تجيب عن هذا الطلب.",
    fieldLabel: "القيمة المطلوبة",
    actionSummary: "تغيير سجل DNS تمت مراجعته.",
    placeholder: "أدخل القيمة التي تمت مراجعتها",
    optionOne: "استخدم النطاق الحالي",
    optionTwo: "أنشئ نطاقًا جديدًا",
  },
};

export const HOMEPAGE_REQUEST_ROTATION_MS = 3_000;

export const HOMEPAGE_REQUESTS = [
  {
    kind: "approval",
    label: { en: "Approve an action", pt: "Aprove uma ação", es: "Aprueba una acción", zh: "批准一项操作", fr: "Approuver une action", de: "Aktion genehmigen", ja: "操作を承認", ar: "وافق على إجراء" },
    signature: "request_approval(title=..., description=...)",
    group: "approval",
  },
  {
    kind: "input:text",
    label: { en: "Give a short answer", pt: "Dê uma resposta curta", es: "Da una respuesta breve", zh: "输入简短回答", fr: "Donner une réponse courte", de: "Kurze Antwort geben", ja: "短い回答を入力", ar: "قدّم إجابة قصيرة" },
    signature: 'request_input(InputRequest(kind="text", ...))',
    group: "input",
  },
  {
    kind: "input:textarea",
    label: { en: "Add the details", pt: "Adicione os detalhes", es: "Añade los detalles", zh: "补充详细信息", fr: "Ajouter les détails", de: "Details ergänzen", ja: "詳細を追加", ar: "أضف التفاصيل" },
    signature: 'request_input(InputRequest(kind="textarea", ...))',
    group: "input",
  },
  {
    kind: "input:password",
    label: { en: "Share a secret safely", pt: "Compartilhe um segredo com segurança", es: "Comparte un secreto de forma segura", zh: "安全地提供密钥", fr: "Partager un secret en toute sécurité", de: "Geheimnis sicher teilen", ja: "シークレットを安全に共有", ar: "شارك سرًا بأمان" },
    signature: 'request_input(InputRequest(kind="password", ...))',
    group: "input",
  },
  {
    kind: "input:phone",
    label: { en: "Add a phone number", pt: "Informe um telefone", es: "Añade un número de teléfono", zh: "添加电话号码", fr: "Ajouter un numéro de téléphone", de: "Telefonnummer angeben", ja: "電話番号を入力", ar: "أضف رقم هاتف" },
    signature: 'request_input(InputRequest(kind="phone", ...))',
    group: "input",
  },
  {
    kind: "input:select",
    label: { en: "Select an option", pt: "Selecione uma opção", es: "Selecciona una opción", zh: "选择一个选项", fr: "Sélectionner une option", de: "Option auswählen", ja: "オプションを選択", ar: "اختر خيارًا" },
    signature: 'request_input(InputRequest(kind="select", ...))',
    group: "input",
  },
  {
    kind: "input:choice",
    label: { en: "Choose one", pt: "Escolha uma", es: "Elige una", zh: "选择一项", fr: "Choisir une option", de: "Eine Option wählen", ja: "1つ選択", ar: "اختر واحدًا" },
    signature: 'request_input(InputRequest(kind="choice", ...))',
    group: "input",
  },
  {
    kind: "input:choices",
    label: { en: "Choose several", pt: "Escolha várias", es: "Elige varias", zh: "选择多项", fr: "Choisir plusieurs options", de: "Mehrere Optionen wählen", ja: "複数選択", ar: "اختر عدة خيارات" },
    signature: 'request_input(InputRequest(kind="choices", ...))',
    group: "input",
  },
  {
    kind: "auth:reauth",
    label: { en: "Confirm your identity", pt: "Confirme sua identidade", es: "Confirma tu identidad", zh: "确认你的身份", fr: "Confirmer votre identité", de: "Identität bestätigen", ja: "本人確認", ar: "أكّد هويتك" },
    signature: 'request_auth("reauth", title=..., description=...)',
    group: "auth",
  },
  {
    kind: "auth:second-factor",
    label: { en: "Enter a security code", pt: "Informe um código de segurança", es: "Introduce un código de seguridad", zh: "输入安全验证码", fr: "Saisir un code de sécurité", de: "Sicherheitscode eingeben", ja: "セキュリティコードを入力", ar: "أدخل رمز الأمان" },
    signature: 'request_auth("second-factor", title=..., description=...)',
    group: "auth",
  },
  {
    kind: "auth:phishing-resistant",
    label: { en: "Use your passkey", pt: "Use sua passkey", es: "Usa tu passkey", zh: "使用你的通行密钥", fr: "Utiliser votre passkey", de: "Passkey verwenden", ja: "パスキーを使用", ar: "استخدم مفتاح المرور" },
    signature: 'request_auth("phishing-resistant", title=..., description=...)',
    group: "auth",
  },
] as const satisfies readonly HomepageRequest[];

export function homepageRequestLabel(request: HomepageRequest, lang: Locale): string {
  return t(request.label, lang);
}

export function homepageRequestChallenge(request: HomepageRequest, lang: Locale) {
  const copy = PREVIEW_COPY[lang];
  const label = homepageRequestLabel(request, lang);
  return {
    challenge_id: `homepage-${request.kind}`,
    expires_in: 300,
    assistant: { id: "shimpz-cloudflare", name: "Shimpz Cloudflare", version: "0.4.1" },
    action: { id: "change-dns-record", summary: copy.actionSummary },
    request: {
      kind: request.kind,
      title: label,
      description: copy.description,
      label: copy.fieldLabel,
      required: true,
      placeholder: request.kind === "input:phone" ? "+1 555 0100" : copy.placeholder,
      min_length: 1,
      max_length: request.kind === "input:textarea" ? 16_000 : request.kind === "input:password" ? 4_096 : 128,
      options: [
        { value: "current", label: copy.optionOne },
        { value: "new", label: copy.optionTwo },
      ],
      min_selections: 1,
      max_selections: 2,
    },
  };
}
