import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Évite d'ajouter @types/node juste pour lire une variable d'environnement de build.
declare const process: { env: Record<string, string | undefined> };

// Le front appelle /api/* ; on proxifie vers le backend FastAPI (même origine → pas de CORS).
// Cible configurable via API_PROXY_TARGET :
//   - dev local        : http://localhost:8000 (défaut)
//   - docker-compose    : http://api:8000 (nom du service)
// Le proxy est appliqué AUSSI en `vite preview` (déploiement conteneur), pas seulement en dev.
const target = process.env.API_PROXY_TARGET || "http://localhost:8000";
const proxy = {
  "/api": {
    target,
    changeOrigin: true,
    rewrite: (p: string) => p.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  // allowedHosts: true → autorise l'accès via le domaine du tunnel Cloudflare
  // (*.trycloudflare.com) en plus de localhost / IP LAN. Acceptable pour un partage de démo.
  server: { port: 5173, host: true, proxy, allowedHosts: true },
  preview: { port: 5173, host: true, proxy, allowedHosts: true },
});
