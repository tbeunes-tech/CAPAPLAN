import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Le front appelle /api/* ; on proxifie vers le backend FastAPI (même origine → pas de CORS).
// Cible configurable via API_PROXY_TARGET :
//   - dev local        : http://localhost:8000 (défaut)
//   - docker-compose    : http://api:8000 (nom du service)
// Le proxy est appliqué AUSSI en `vite preview` (déploiement conteneur), pas seulement en dev.
var target = process.env.API_PROXY_TARGET || "http://localhost:8000";
var proxy = {
    "/api": {
        target: target,
        changeOrigin: true,
        rewrite: function (p) { return p.replace(/^\/api/, ""); },
    },
};
export default defineConfig({
    plugins: [react()],
    server: { port: 5173, proxy: proxy },
    preview: { port: 5173, host: true, proxy: proxy },
});
