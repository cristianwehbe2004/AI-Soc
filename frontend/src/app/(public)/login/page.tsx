"use client";

import { AuthLoading } from "@/components/auth/auth-loading";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api/client";
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, UserPlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState, useTransition } from "react";

type AuthMode = "signin" | "signup";

export default function LoginPage() {
  const { status, login, register } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("signin");
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
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");

    if (mode === "signup") {
      const fullName = String(form.get("full_name") ?? "").trim();
      const confirmPassword = String(form.get("confirm_password") ?? "");

      if (!fullName) {
        setError("Full name is required.");
        return;
      }
      if (password.length < 12) {
        setError("Password must be at least 12 characters long.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }

      startTransition(async () => {
        try {
          await register(fullName, email, password);
          router.replace("/dashboard");
        } catch (caught) {
          if (caught instanceof ApiError && caught.status === 429) {
            setError("Too many registration attempts. Wait 15 minutes before trying again.");
          } else if (caught instanceof ApiError && caught.status === 409) {
            setError("An account with this email address already exists.");
          } else if (caught instanceof ApiError && caught.body) {
            setError(caught.message || "Could not create account.");
          } else {
            setError("AI-SOC is unavailable. Check the backend and try again.");
          }
        }
      });
    } else {
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
        <div className="login-form">
          <div className="mode-tabs" style={{ display: "flex", gap: "8px", marginBottom: "24px", background: "var(--surface-muted, #f1f5f9)", padding: "4px", borderRadius: "10px" }}>
            <button
              type="button"
              onClick={() => { setMode("signin"); setError(null); }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "8px",
                border: "none",
                fontWeight: 600,
                fontSize: "14px",
                cursor: "pointer",
                background: mode === "signin" ? "#ffffff" : "transparent",
                color: mode === "signin" ? "#0f172a" : "#64748b",
                boxShadow: mode === "signin" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                transition: "all 0.2s"
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode("signup"); setError(null); }}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "8px",
                border: "none",
                fontWeight: 600,
                fontSize: "14px",
                cursor: "pointer",
                background: mode === "signup" ? "#ffffff" : "transparent",
                color: mode === "signup" ? "#0f172a" : "#64748b",
                boxShadow: mode === "signup" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                transition: "all 0.2s"
              }}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-heading">
              <p className="eyebrow">{mode === "signin" ? "Analyst access" : "New Account Setup"}</p>
              <h2>{mode === "signin" ? "Sign in to the console" : "Create analyst account"}</h2>
              <p>
                {mode === "signin"
                  ? "Use an account created by your AI-SOC administrator or sign up."
                  : "Register a new analyst account to begin investigating."}
              </p>
            </div>

            {mode === "signup" && (
              <>
                <label className="field-label" htmlFor="full_name">Full Name</label>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  autoComplete="name"
                  required
                  placeholder="Jane Doe"
                  style={{ marginBottom: "16px" }}
                />
              </>
            )}

            <label className="field-label" htmlFor="email">Email address</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              required
              placeholder="analyst@example.com"
              style={{ marginBottom: "16px" }}
            />

            <label className="field-label" htmlFor="password">Password</label>
            <div className="password-field" style={{ marginBottom: mode === "signup" ? "16px" : "0" }}>
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                required
                minLength={12}
                placeholder="Minimum 12 characters"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {mode === "signup" && (
              <>
                <label className="field-label" htmlFor="confirm_password">Confirm Password</label>
                <div className="password-field">
                  <input
                    id="confirm_password"
                    name="confirm_password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    minLength={12}
                    placeholder="Re-enter your password"
                  />
                </div>
              </>
            )}

            {error && <div className="form-error" role="alert" style={{ marginTop: "16px" }}>{error}</div>}

            <button className="primary-button" type="submit" disabled={isPending} style={{ marginTop: "24px" }}>
              <span>
                {isPending
                  ? mode === "signin"
                    ? "Verifying identity..."
                    : "Creating account..."
                  : mode === "signin"
                  ? "Enter operations"
                  : "Complete Sign Up"}
              </span>
              {mode === "signin" ? <ArrowRight size={18} /> : <UserPlus size={18} />}
            </button>
            <p className="form-footnote">Authentication activity is security audited.</p>
          </form>
        </div>
      </section>
    </main>
  );
}
