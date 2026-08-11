import type { Locale } from "$lib/catalog";
import { tr } from "$lib/i18n";

export function humanRequestKicker(kind: string, lang: Locale): string {
  return tr(
    kind.startsWith("auth:")
      ? "human_auth_kicker"
      : kind.startsWith("input:")
        ? "human_input_kicker"
        : "human_approval_kicker",
    lang,
  );
}

export function humanRequestPrimaryLabel(kind: string, lang: Locale): string {
  return tr(
    kind === "approval"
      ? "human_approve"
      : kind === "auth:phishing-resistant"
        ? "human_passkey"
        : kind.startsWith("auth:")
          ? "human_authorize"
          : "human_submit",
    lang,
  );
}

export function humanRequestFieldLabels(request: Record<string, any>, lang: Locale) {
  return {
    required: tr("human_required", lang),
    optional: tr("human_optional", lang),
    chooseOption: tr("human_choose", lang),
    selectionHint: `${tr("human_selection_hint", lang)} ${request.min_selections ?? 0}–${request.max_selections ?? 0}`,
    thirdPartySecret: tr("human_third_party_secret", lang),
    reauthHint: tr("human_reauth_hint", lang),
    reauthLabel: tr("human_password_label", lang),
    secondFactorHint: tr("human_totp_hint", lang),
    secondFactorLabel: tr("human_totp_label", lang),
    secondFactorPlaceholder: tr("human_totp_placeholder", lang),
    passkeyHint: tr("human_passkey_hint", lang),
  };
}
