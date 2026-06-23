import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { useWindowStart } from "./WindowContext";
import LoginPage from "./pages/LoginPage";

const TABS: { to: string; label: string }[] = [
  { to: "/portfolio", label: "Portefeuille" },
  { to: "/team-load", label: "Charge équipe" },
  { to: "/capacity", label: "Capacité" },
  { to: "/occupancy", label: "Taux d'occupation" },
  { to: "/overloads", label: "Surcharges" },
  { to: "/roadmap", label: "Roadmap" },
  { to: "/prioritization", label: "Priorisation" },
];

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin", contributor: "Contributeur", reader: "Lecteur",
};

export default function App() {
  const { email, role, logout, can } = useAuth();
  const { start, setStart } = useWindowStart();

  if (!email) return <LoginPage />;

  // Onglet Admin (gestion des équipes §3.3) visible aux seuls Admin.
  const tabs = can("admin") ? [...TABS, { to: "/teams", label: "Équipes" }] : TABS;

  return (
    <div className="app">
      <header className="topbar">
        <h1>Portefeuille DSI</h1>
        <nav className="tabs">
          {tabs.map((t) => (
            <NavLink key={t.to} to={t.to}>
              {t.label}
            </NavLink>
          ))}
        </nav>
        <label className="window-picker" title="Mois de départ de la fenêtre 12 mois (§6.3)">
          Fenêtre&nbsp;:
          <input
            type="month"
            value={start.slice(0, 7)}
            onChange={(e) => setStart(e.target.value ? `${e.target.value}-01` : "")}
          />
        </label>
        <div className="user-box">
          <span className="muted">
            {email} · <strong>{ROLE_LABEL[role ?? ""] ?? role}</strong>
          </span>
          <button onClick={logout}>Déconnexion</button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
