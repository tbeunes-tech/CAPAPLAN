"""Point d'entrée FastAPI.

Lots 2–5 : CRUD projets/charge (§5.1/§5.2), dashboards (§5.3–5.8), règles §6, QC §7,
auth + 3 rôles (§8.1), journal d'audit (§8.2).
"""
from __future__ import annotations

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .audit import current_user, register_audit
from .config import settings
from .routers import (
    audit_log, auth, capacity, dashboards, projects, referentials, teams,
)
from .security import decode_access_token

register_audit()  # historisation §8.2 — écouteurs SQLAlchemy globaux

app = FastAPI(title="Portefeuille Projets DSI", version="0.5.0 (Lot 5 — auth, rôles, audit)")

# CORS : nécessaire quand le front est servi depuis une autre origine (déploiement cloud où le
# front appelle l'API par son URL publique). En dev (proxy Vite, même origine), la liste est vide.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],          # dont Authorization (jeton Bearer, pas de cookie)
        allow_credentials=False,
    )


@app.middleware("http")
async def attach_audit_user(request: Request, call_next):
    """Pose l'utilisateur courant (depuis le JWT) dans le contexte de la requête, pour que
    le journal d'audit (§8.2) l'attribue correctement même quand l'endpoint s'exécute dans
    le threadpool. Le contexte async de la requête est copié vers le thread d'exécution."""
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        try:
            current_user.set(decode_access_token(auth.split(" ", 1)[1]).get("sub", "system"))
        except jwt.PyJWTError:
            pass
    return await call_next(request)

app.include_router(auth.router)
app.include_router(referentials.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(capacity.router)
app.include_router(dashboards.router)
app.include_router(audit_log.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "lot": 5, "database_url_scheme": settings.database_url.split(":", 1)[0]}
