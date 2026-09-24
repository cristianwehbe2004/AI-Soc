"use client";

import { AuthLoading } from "@/components/auth/auth-loading";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api/client";
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState, useTransition } from "react";

export default function LoginPage() {
  const { status, login } = useAuth();
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [router, status]);

  if (status === "loading") return <AuthLoading />;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");

    startTransition(async () => {
      try {
        await login(email, password);
        router.replace("/dashboard");
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 429) {
          setError("Too many attempts. Wait 15 minutes before trying again.");
        } else if (caught instanceof ApiError && caught.status === 401) {
          setError("The email or password is incorrect.");
        } else {
          setError("AI-SOC is unavailable. Check the backend and try again.");
        }
      }
    });
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand-lockup login-brand">
          <div className="brand-mark"><LockKeyhole size={21} /></div>
          <div><strong>AI-SOC</strong><span>Security operations</span></div>
        </div>
        <div className="story-copy">
          <p className="eyebrow">Evidence over noise</p>
          <h1>See the attack path.<br />Act with context.</h1>
          <p>Detection, anomaly scoring, incident correlation, ATT&amp;CK context, and AI investigation in one defensive workspace.</p>
        </div>
        <div className="story-signal" aria-hidden="true">
          <span className="signal-line one" /><span className="signal-line two" /><span className="signal-line three" />
          <div className="signal-node node-a" /><div className="signal-node node-b" /><div className="signal-node node-c" />
        </div>
        <div className="security-note"><ShieldCheck size={18} /><span>Access tokens stay in memory. Refresh sessions remain HttpOnly.</span></div>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-heading">
            <p className="eyebrow">Analyst access</p>
            <h2>Sign in to the console</h2>
            <p>Use an account created by your AI-SOC administrator.</p>
          </div>
          <label className="field-label" htmlFor="email">Email address</label>
          <input id="email" name="email" type="email" autoComplete="username" required placeholder="analyst@example.com" />
          <label className="field-label" htmlFor="password">Password</label>
          <div className="password-field">
            <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required minLength={12} placeholder="Enter your password" />
            <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary-button" type="submit" disabled={isPending}>
            <span>{isPending ? "Verifying identity..." : "Enter operations"}</span>
            <ArrowRight size={18} />
          </button>
          <p className="form-footnote">Authentication activity is security audited.</p>
        </form>
      </section>
    </main>
  );
}
