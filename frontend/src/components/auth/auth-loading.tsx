export function AuthLoading() {
  return (
    <main className="auth-loading" aria-live="polite">
      <div className="signal-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="eyebrow">Secure session</p>
      <h1>Restoring your workspace</h1>
      <p>Verifying the encrypted refresh session with AI-SOC.</p>
    </main>
  );
}
