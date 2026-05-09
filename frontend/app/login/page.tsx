"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest, authEnabled } from "../../lib/api";

type SessionResponse = {
  auth_enabled: boolean;
  authenticated: boolean;
  username?: string | null;
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("operator");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      await apiRequest<SessionResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      router.replace("/");
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  if (!authEnabled) {
    return (
      <main className="auth-shell">
        <div className="auth-card">
          <span className="eyebrow">Authentication disabled</span>
          <h1>Local operator access is open.</h1>
          <p>
            `NEXT_PUBLIC_AUTH_ENABLED` is off, so the frontend is not requiring a
            login gate right now.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <form className="auth-card" onSubmit={handleSubmit}>
        <span className="eyebrow">Operator login</span>
        <h1>Secure the terminal before cloud testing.</h1>
        <p>
          Sign in with the operator credentials configured on the backend to reach the
          trading workspace.
        </p>
        <div className="form-grid">
          <label className="field">
            <span>Username</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
        </div>
        {error ? <div className="callout callout-error">{error}</div> : null}
        <div className="actions form-actions">
          <button className="button" type="submit" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </div>
      </form>
    </main>
  );
}
