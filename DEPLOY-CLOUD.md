# Déploiement cloud (URL publique)

> ⚠️ **Données client** : ce déploiement met les données réelles du portefeuille sur un cloud
> tiers. S'assurer que la DSI autorise un hébergement externe. Les **comptes de démo ne sont PAS
> créés** en cloud — on crée des comptes nominatifs (étape 5).

On déploie sur **Render** (gratuit pour tester, HTTPS automatique) : une base PostgreSQL, l'API
FastAPI et le front React statique. Architecture : le front (statique) appelle l'API par son URL
publique (`VITE_API_BASE`), l'API autorise cette origine (CORS via `CORS_ORIGINS`).

## Prérequis (côté toi)
1. Un compte **GitHub** et un compte **Render** (render.com), gratuits.
2. Pousser le dépôt sur GitHub (le repo est déjà prêt, `git init` + 1er commit faits) :
   ```bash
   cd "portfolio-dsi"
   git remote add origin https://github.com/<toi>/portfolio-dsi.git
   git push -u origin main
   ```
   Les données sensibles ne partent pas (`.env`, `*.db`, le classeur `.xlsm` sont gitignorés).

## Déploiement
3. Sur Render → **New > Blueprint** → choisir ton repo GitHub. Render lit `render.yaml` et crée :
   `portfolio-db` (Postgres), `portfolio-api` (API), `portfolio-front` (front).
4. Renseigner les 2 variables croisées (Render demande celles en `sync:false`) :
   - sur **portfolio-front** → `VITE_API_BASE` = URL de l'API, ex. `https://portfolio-api.onrender.com`
   - sur **portfolio-api** → `CORS_ORIGINS` = URL du front, ex. `https://portfolio-front.onrender.com`
   Puis redéployer le front (pour qu'il prenne `VITE_API_BASE` au build).

## Charger les données + créer ton compte (une fois la base créée)
5. Récupère l'**External Database URL** de `portfolio-db` (dashboard Render), puis depuis ton Mac :
   ```bash
   cd portfolio-dsi/backend && source .venv/bin/activate
   export DATABASE_URL="postgresql+psycopg2://...render.com/portfolio"   # External URL (+psycopg2)
   alembic upgrade head                                                   # si pas déjà fait
   python -m scripts.migrate_from_xlsm "/chemin/PORTFOLIO....xlsm"        # importe le portefeuille
   python -m scripts.manage_users create --email toi@dsi.fr --password '<fort>' --role admin
   # comptes nominatifs pour les testeurs (Contributeur / Lecteur) :
   python -m scripts.manage_users create --email collegue@dsi.fr --password '<fort>' --role contributor
   ```
   > Alternative : copier la base locale telle quelle —
   > `pg_dump -Fc "$LOCAL_URL" | pg_restore --no-owner -d "$CLOUD_URL"`.

## Sécurité avant de partager l'URL
- ✅ HTTPS : automatique sur Render.
- ✅ `JWT_SECRET` : généré par Render (ne pas utiliser la valeur de dev).
- ✅ Pas de comptes de démo : seulement des comptes nominatifs (étape 5).
- 🔁 Sauvegarde : planifier `scripts/backup.py` (cron Render ou job externe) contre l'URL cloud.

## Notes plan gratuit
- L'API se met en **veille** après inactivité → 1er accès ~30 s (cold start).
- La **base gratuite expire** (~30 j) ; passer en plan payant pour un usage durable.
