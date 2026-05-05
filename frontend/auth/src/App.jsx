import { useMemo, useState } from "react";

const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || "http://localhost:8002";

const roleDetails = {
  kitten: {
    title: "Kitten",
    description: "Solve problems, earn fishing chances, collect fish, and use Cat Can Tokens.",
    redirect: "/quiz",
  },
  cat: {
    title: "Cat",
    description: "Create fish ponds, manage problems, and invite kittens without token economy access.",
    redirect: "/teacher",
  },
};

async function postJson(path, payload) {
  const response = await fetch(`${AUTH_SERVICE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

export default function App() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [role, setRole] = useState("kitten");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [session, setSession] = useState(null);

  const selectedRole = useMemo(() => roleDetails[role], [role]);
  const canSend = email.trim().length > 3;
  const canVerify = canSend && code.trim().length === 6;

  async function sendCode() {
    setStatus("loading");
    setMessage("");
    try {
      const result = await postJson("/auth/send-verification-email", {
        email: email.trim(),
        role,
      });
      setStatus("code_sent");
      setMessage(
        result.email_sent
          ? "Verification code sent."
          : "Verification code created. SMTP is not configured, so no email was sent."
      );
    } catch (error) {
      setStatus("error");
      setMessage(error.message);
    }
  }

  async function verifyCode() {
    setStatus("loading");
    setMessage("");
    try {
      const result = await postJson("/auth/verify-email", {
        email: email.trim(),
        code: code.trim(),
        role,
      });
      localStorage.setItem("catch_auth_token", result.token);
      localStorage.setItem("catch_user_role", result.role);
      localStorage.setItem("catch_user_id", result.user_id);
      setSession(result);
      setStatus("verified");
      setMessage("Signed in.");
    } catch (error) {
      setStatus("error");
      setMessage(error.message);
    }
  }

  return (
    <main className="auth-shell">
      <section className="hero">
        <p className="eyebrow">CatCh account</p>
        <h1>Sign in with email</h1>
        <p className="lede">
          Choose kitten for gameplay or cat for classroom management. Cats do not use
          Cat Can Tokens or marketplace features.
        </p>
      </section>

      <section className="auth-panel">
        <div className="role-grid" aria-label="Choose role">
          {Object.entries(roleDetails).map(([value, detail]) => (
            <button
              className={role === value ? "role-card selected" : "role-card"}
              key={value}
              type="button"
              onClick={() => setRole(value)}
            >
              <strong>{detail.title}</strong>
              <span>{detail.description}</span>
            </button>
          ))}
        </div>

        <label>
          Email
          <input
            autoComplete="email"
            inputMode="email"
            placeholder="you@example.com"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <div className="actions">
          <button disabled={!canSend || status === "loading"} type="button" onClick={sendCode}>
            Send Code
          </button>
        </div>

        <label>
          Verification code
          <input
            inputMode="numeric"
            maxLength={6}
            placeholder="123456"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>

        <div className="actions">
          <button disabled={!canVerify || status === "loading"} type="button" onClick={verifyCode}>
            Verify
          </button>
        </div>

        {message ? <p className={`message ${status}`}>{message}</p> : null}

        {session ? (
          <section className="session-card">
            <h2>{selectedRole.title} session</h2>
            <dl>
              <div>
                <dt>User ID</dt>
                <dd>{session.user_id}</dd>
              </div>
              <div>
                <dt>Token system</dt>
                <dd>{session.token_system_enabled ? "Enabled" : "Disabled"}</dd>
              </div>
              <div>
                <dt>Next route</dt>
                <dd>{selectedRole.redirect}</dd>
              </div>
            </dl>
          </section>
        ) : null}
      </section>
    </main>
  );
}
