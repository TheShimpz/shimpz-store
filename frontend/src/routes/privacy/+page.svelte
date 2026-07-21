<script lang="ts">
  import LegalPage from "$lib/components/LegalPage.svelte";
</script>

<LegalPage
  title="Privacy Policy"
  path="/privacy"
  description="How Shimpz collects, uses, protects, and shares information when you use the Shimpz platform."
  effectiveDate="July 20, 2026"
>
  <section>
    <h2>1. Scope</h2>
    <p>
      This Privacy Policy applies to Shimpz websites, accounts, Teams, Assistants, and related platform
      features that link to it. It does not replace the privacy terms of a third-party service you choose
      to connect, such as an AI model provider or an OAuth provider.
    </p>
  </section>

  <section>
    <h2>2. Information we process</h2>
    <ul>
      <li><strong>Account information:</strong> email address, password verifier, session data, and account status.</li>
      <li><strong>Team content:</strong> Team settings, chat messages, files, instructions, and Assistant results you submit or create.</li>
      <li><strong>Connected accounts:</strong> provider identity, approved scopes, connection status, token expiry, and OAuth access or refresh tokens.</li>
      <li><strong>Configuration:</strong> model-provider choices, Assistant installations, approvals, and resource settings.</li>
      <li><strong>Security records:</strong> bounded logs about requests, authentication, changes, failures, and suspected abuse.</li>
    </ul>
  </section>

  <section>
    <h2>3. How we use information</h2>
    <p>We process information to:</p>
    <ul>
      <li>create and secure your account and Teams;</li>
      <li>perform the operations you request through Assistants and connected providers;</li>
      <li>maintain, troubleshoot, audit, and improve the platform;</li>
      <li>detect abuse, protect users, and enforce platform limits; and</li>
      <li>comply with applicable legal obligations.</li>
    </ul>
  </section>

  <section>
    <h2>4. OAuth and connected providers</h2>
    <p>
      Connecting a provider is optional. Shimpz requests only reviewed scopes and uses the resulting grant
      to perform operations you authorize. We do not sell OAuth data. We do not use connected-account data
      for advertising. You may disconnect a provider, and you may also revoke Shimpz from that provider's
      authorization settings.
    </p>
    <p>
      Provider tokens are treated as protected credentials. They are kept outside public responses and are
      disclosed only to the bounded internal execution path needed for an authorized operation.
    </p>
  </section>

  <section>
    <h2>5. AI model providers</h2>
    <p>
      When you ask a Team to perform work, relevant instructions, messages, files, and context may be sent
      to the AI model provider selected for that Team. That provider processes the information under its own
      terms and privacy policy. Avoid submitting information that is not needed for your request.
    </p>
  </section>

  <section>
    <h2>6. When information is shared</h2>
    <p>We share information only as needed:</p>
    <ul>
      <li>with providers you select, to complete an operation you request;</li>
      <li>with infrastructure vendors that process data for the platform under appropriate restrictions;</li>
      <li>when you direct us to share it or collaborate with another authorized user; or</li>
      <li>when reasonably necessary to comply with law, protect rights, or prevent harm.</li>
    </ul>
    <p>We do not sell personal information.</p>
  </section>

  <section>
    <h2>7. Retention and deletion</h2>
    <p>
      We retain information while your account, Team, or provider connection is active and for only as long
      afterward as reasonably necessary for security, recovery, dispute resolution, or legal obligations.
      Disconnecting a provider stops new use of its grant. Deleting a Team or account may not immediately
      remove bounded backup or security records, which expire under their applicable retention cycle.
    </p>
  </section>

  <section>
    <h2>8. Security</h2>
    <p>
      Shimpz uses access controls, encryption, scoped credentials, network isolation, secret redaction, and
      audit controls designed to protect information. No system is perfectly secure, so you should use a
      unique password, protect your sessions, and promptly revoke access you no longer trust.
    </p>
  </section>

  <section>
    <h2>9. Your choices and rights</h2>
    <p>
      You can review account and Team information, disconnect providers, revoke provider authorization, and
      request account deletion. Depending on where you live, you may also have rights to access, correct,
      delete, restrict, object to, or receive a copy of personal information.
    </p>
  </section>

  <section>
    <h2>10. Children</h2>
    <p>
      Shimpz is not directed to children under 13, and we do not knowingly collect their personal
      information. A higher minimum age may apply where required by local law.
    </p>
  </section>

  <section>
    <h2>11. Changes</h2>
    <p>
      We may update this policy as the platform changes. The effective date above identifies the current
      version. Material changes will be presented through an appropriate platform or website notice.
    </p>
  </section>

  <section>
    <h2>12. Contact</h2>
    <p>
      For privacy questions or requests, contact
      <a href="mailto:privacy@shimpz.com">privacy@shimpz.com</a>.
    </p>
  </section>
</LegalPage>
