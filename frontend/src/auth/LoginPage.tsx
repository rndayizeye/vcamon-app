import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "./use-auth";
import { AuthStatusBanner } from "./AuthStatusBanner";
import { hasSupabaseClientConfig, supabase } from "../lib/supabase";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { authenticated, backendAuthEnabled, loading, status } = useAuth();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const from = useMemo(() => {
    const next = (location.state as { from?: string } | null)?.from;
    return typeof next === "string" && next ? next : "/cases";
  }, [location.state]);

  useEffect(() => {
    if (authenticated) {
      navigate(from, { replace: true });
    }
  }, [authenticated, from, navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      if (!supabase || !hasSupabaseClientConfig) {
        throw new Error(
          "Supabase client configuration is missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.",
        );
      }

      const { error: signInError } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin,
        },
      });

      if (signInError) {
        throw signInError;
      }

      setMessage("Check your email for the sign-in link.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start sign-in");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card stack-lg">
        <div className="stack-sm">
          <p className="eyebrow">VCA Monitor</p>
          <h1>Sign in</h1>
          <p className="muted">
            Sign in to access the case management system.
          </p>
        </div>

        <AuthStatusBanner />

        {!backendAuthEnabled && !loading ? (
          <div className="stack-sm">
            <p>
              No sign-in required in this environment — continue directly to the app.
            </p>
            <Link className="button button-primary" to="/cases">
              Continue to cases
            </Link>
          </div>
        ) : null}

        {backendAuthEnabled ? (
          <form className="stack-md" onSubmit={handleSubmit}>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="worker@example.com"
                required
              />
            </label>

            <button
              className="button button-primary"
              type="submit"
              disabled={
                submitting ||
                !status?.ready ||
                !hasSupabaseClientConfig ||
                !email
              }
            >
              {submitting ? "Sending link…" : "Send sign-in link"}
            </button>
          </form>
        ) : null}

        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}

        <p className="muted small-text">
          Already signed in? <Link to="/cases">Go to the case list</Link>.
        </p>
      </section>
    </main>
  );
}
