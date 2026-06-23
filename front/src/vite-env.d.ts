/// <reference types="vite/client" />

interface ImportMetaEnv {
  // URL publique de l'API en déploiement cloud (ex. https://portfolio-api.onrender.com).
  // Vide en dev/LAN → on utilise le proxy Vite "/api".
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
