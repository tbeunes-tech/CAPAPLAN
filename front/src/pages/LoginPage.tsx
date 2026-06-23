import { useState } from "react";
import { useAuth } from "../AuthContext";

const DEMO = [
  ["admin@demo.fr", "admin123", "Admin"],
  ["contrib@demo.fr", "contrib123", "Contributeur"],
  ["reader@demo.fr", "reader123", "Lecteur"],
];

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@demo.fr");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>Portefeuille Projets DSI</h1>
        <p className="muted">Connexion (§8.1)</p>
        <div className="field">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        </div>
        <div className="field">
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p className="err">⚠ {error}</p>}
        <button className="primary" disabled={busy} type="submit">
          {busy ? "Connexion…" : "Se connecter"}
        </button>
        <div className="demo-accounts">
          <span className="muted">Comptes de démo :</span>
          {DEMO.map(([em, pw, label]) => (
            <button
              type="button"
              key={em}
              onClick={() => {
                setEmail(em);
                setPassword(pw);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </form>
    </div>
  );
}
