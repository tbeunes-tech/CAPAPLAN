# Portefeuille Projets DSI — application web

Refonte d'un classeur Excel macro (`PORTFOLIO PROJETS DSI V_4_02.xlsm`) en application web
multi-utilisateur. **Objectif n°1 :** saisie/consultation concurrente sans verrou de fichier ni
perte de données. Spec de référence : [`SPEC.md`](./SPEC.md) · avancement : [`AGENTS.md`](./AGENTS.md).

> **État : Lot 1 — Socle données.** Schéma 4 tables + migration Alembic + import du classeur +
> tests des règles §6.1/§6.2 (et §6.5/§6.7). En attente de validation du schéma avant le Lot 2.

## Stack
PostgreSQL (prod) / SQLite (dev) · FastAPI · SQLAlchemy 2.0 + Alembic · Pydantic · pytest.

## Démarrage rapide (dev, SQLite, sans Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Créer le schéma
export DATABASE_URL=sqlite:///./portfolio.db
alembic upgrade head

# 2) Importer les données du classeur (§9)
python -m scripts.migrate_from_xlsm "/chemin/PORTFOLIO PROJETS DSI V_4_02.xlsm"

# 3) Lancer l'API
uvicorn app.main:app --reload      # http://127.0.0.1:8000/health

# 4) Tests des règles de gestion (§6) — base SQLite en mémoire
python -m pytest
```

## Front (Lot 3 — portefeuille + saisie)

```bash
cd front
npm install
npm run dev          # http://localhost:5173  (proxy /api → backend :8000)
```

Écrans livrés (barre d'onglets en haut) :
- **5.1 Portefeuille** — table filtrable/triable, lignes en erreur QC surlignées, CRUD via formulaire §4.
- **5.2 Saisie de charge** — grille équipes × mois ; n'envoie que les cellules modifiées → saisie
  **concurrente** sans collision (objectif n°1).
- **5.3 Charge équipe**, **5.4 Capacité**, **5.5 Taux d'occupation** (table colorée + graphe Recharts),
  **5.6 Surcharges**, **5.7 Roadmap (Gantt)**, **5.8 Priorisation** — lecture seule, recalculés à la volée.

Un sélecteur **« Fenêtre »** (mois de départ) en haut à droite pilote la fenêtre 12 mois de tous
les dashboards. Auth/rôles, historisation et sauvegarde → Lot 5.

## Démarrage avec Docker (PostgreSQL)

```bash
docker compose up --build          # db + api ; applique les migrations au boot
# puis importer le classeur dans le conteneur api :
docker compose exec api python -m scripts.migrate_from_xlsm "/data/PORTFOLIO....xlsm"
```

## Le script de migration (`scripts/migrate_from_xlsm.py`)

Alimente les 4 tables depuis les onglets `Project Portfolio 25-26`, `Détail Mensuel`,
`Equipes`, `Détail Capa Mensuelle`. **Idempotent** (upsert par clé). Options :
`--database-url <url>`, `--reset` (vide les tables avant import). Affiche un rapport
(counts, équipes *stub* créées, lignes ignorées).

## Choix de modélisation (Lot 1)

- **4 tables persistées** (§3) ; toutes les restitutions (§5.3–5.8) sont calculées à la volée.
- Référentiels §4 : colonnes **texte** validées contre `app/enums.py` (édition Admin en Lot 5
  sans migration), plutôt qu'un `ENUM` SQL figé.
- Colonnes calculées (`in_plan`, `last_update`, `total_project_load`, `capa_projet`) : **jamais
  saisies** ; recalculées par l'app. À l'import, snapshot fidèle du classeur puis recalcul.
- Règles **arrêtées** : §6.5 jours ouvrés = lundi→vendredi **fériés inclus** ; §6.7 ne pondère
  que l'indispo par la part projet (le commentaire VBA d'en-tête est erroné — ignoré).

## Authentification & rôles (§8.1)

3 rôles : **admin** (tout + référentiels/équipes/capacités/seuils), **contributor** (CRUD projets +
saisie de charge), **reader** (lecture seule des dashboards). Auth par **JWT** (`POST /auth/login`).

```bash
# Créer des comptes
python -m scripts.manage_users seed-demo          # admin/contributor/reader de démo
python -m scripts.manage_users create --email moi@dsi.fr --password '***' --role admin
```
> En production, définir `JWT_SECRET` via l'environnement (jamais la valeur par défaut de dev).

## Historisation des modifications (§8.2)

Chaque écriture sur `projects`, `monthly_loads`, `teams`, `monthly_capacity` génère
automatiquement une ligne `change_log` (**qui · quand · table · clé · avant → après**), via des
écouteurs SQLAlchemy (`app/audit.py`). Consultation réservée Admin : `GET /audit?table_name=…&row_pk=…`.
On peut ainsi reconstituer l'état d'un projet ou d'une charge à n'importe quelle date. L'import
massif (`migrate_from_xlsm`) n'est pas journalisé.

## Sauvegarde quotidienne automatique (§8.3)

```bash
python -m scripts.backup --out /var/backups/portfolio --retention-days 30
```
Génère un dump `pg_dump -Fc` horodaté, applique une rétention glissante (30 j), journalise
succès/échec et **sort en code ≠ 0 en cas d'échec** (pour alerte). Planifier vers un volume
**distinct** du serveur applicatif. Exemple cron (02h00) :
```cron
0 2 * * *  cd /app/backend && DATABASE_URL=postgresql://… \
           /app/.venv/bin/python -m scripts.backup --out /var/backups/portfolio \
           >> /var/log/portfolio-backup.log 2>&1 || curl -s "$ALERT_WEBHOOK" -d "backup KO"
```

### Mise en place locale (poste de test macOS)

Sur le poste de test, la sauvegarde tourne via **launchd** (équivalent natif de cron) :
`~/Library/LaunchAgents/com.portfolio-dsi.backup.plist` lance `backend/scripts/run_backup.sh`
chaque jour à 02:00 → dumps `pg_dump -Fc` dans `~/portfolio-backups/` (rétention 30 j).
Activer / désactiver :
```bash
launchctl load -w  ~/Library/LaunchAgents/com.portfolio-dsi.backup.plist
launchctl unload   ~/Library/LaunchAgents/com.portfolio-dsi.backup.plist
bash backend/scripts/run_backup.sh        # sauvegarde manuelle immédiate
```

## Reprise après incident (§8.4)

Toute écriture est **transactionnelle** : une coupure en cours de saisie ne laisse jamais la base
dans un état partiel (soit la transaction est validée, soit annulée) — c'est ce qui supprime le
problème de « fichier à moitié écrit » du classeur. Deux niveaux de restauration :

1. **Depuis le dernier dump quotidien (RPO ≤ 24 h)** :
   ```bash
   createdb portfolio_restore
   pg_restore --no-owner --dbname=portfolio_restore /var/backups/portfolio/portfolio-AAAAMMJJ-HHMMSS.dump
   # valider, puis basculer l'application sur portfolio_restore
   ```
2. **Point-in-time recovery (PITR)** pour revenir juste avant l'incident : activer l'archivage WAL
   sur le serveur PostgreSQL (`wal_level=replica`, `archive_mode=on`, `archive_command=…`), puis
   restaurer un base backup + rejouer les WAL jusqu'à `recovery_target_time` choisi
   (`restore_command` + `recovery_target_time='AAAA-MM-JJ HH:MM:SS'`). Voir la doc PostgreSQL
   « Continuous Archiving and Point-in-Time Recovery ».
