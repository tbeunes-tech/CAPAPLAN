"""Configuration applicative (§2).

`DATABASE_URL` pilote la cible :
- PostgreSQL en prod : ``postgresql+psycopg2://user:pass@host:5432/portfolio``
- SQLite en dev/local (défaut)  : ``sqlite:///./portfolio.db``
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./portfolio.db"

    # Seuils de couleur du taux d'occupation (§5.5), paramétrables par un Admin.
    occupancy_green_below: float = 0.80   # < 80 % → vert
    occupancy_amber_below: float = 1.00   # 80–100 % → ambre ; > 100 % → rouge

    # Auth (§8.1). En prod, JWT_SECRET DOIT être défini via l'environnement.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 8 * 60

    # CORS : origines autorisées (séparées par des virgules). Vide en dev (même origine via proxy
    # Vite). En cloud, mettre l'URL du front, ex. "https://portfolio-front.onrender.com".
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
