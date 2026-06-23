# AGENTS.md — État d'avancement & conventions

Application de pilotage du **portefeuille projets DSI** (refonte d'un classeur Excel macro
multi-onglets vers une app web multi-utilisateur). Spec de référence : [`SPEC.md`](./SPEC.md).

## Objectif n°1 (non négociable)
Saisie/consultation **concurrente** sans verrou de fichier ni perte de données. Toute écriture
est transactionnelle. C'est la raison d'être de la refonte.

## Stack
- DB : PostgreSQL (prod) / SQLite (dev & tests).
- Backend : Python + FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic. (`backend/`)
- Front : React + TypeScript + Vite, TanStack Table + TanStack Query. (`front/`)

## Lancer le front (dev)
```bash
# 1) backend lancé sur :8000 (cf. README) avec la base migrée
cd front && npm install && npm run dev      # http://localhost:5173
```
Le front appelle `/api/*` proxifié vers `:8000` (cf. `vite.config.ts`) — pas de CORS en dev.

### Écrans (barre d'onglets, `App.tsx`)
Portefeuille (5.1) · Charge équipe (5.3) · Capacité (5.4) · Taux d'occupation (5.5, +graphe
Recharts) · Surcharges (5.6) · Roadmap Gantt (5.7) · Priorisation (5.8). Le **mois de départ**
de la fenêtre 12 mois est un sélecteur global (`WindowContext`) partagé entre tous les onglets.
Les dashboards sont en lecture seule, recalculés via l'API `/dashboards/*` et `/capacity/pivot`.
**Exception (§5.4) :** l'écran Capacité est éditable par les **Admin** — clic sur une cellule →
modale d'édition des entrées (ETP équipe, ETP projet, jours indispo) ; `capa_projet` est recalculée
côté serveur (§6.7) avec un aperçu live côté client. Endpoints : `GET /capacity/cell`, `PUT /capacity`.

### Auth front (Lot 5)
Écran de connexion (boutons comptes de démo), jeton JWT en `localStorage`, en-tête `Authorization`
injecté par `api.ts`, déconnexion sur 401. Les boutons d'écriture sont masqués/désactivés selon le
rôle (`AuthContext.can()`). Comptes de démo : `python -m scripts.manage_users seed-demo`.

### Historique projet (§8.2)
Bouton **« Hist. »** sur chaque ligne du portefeuille → `/portfolio/{id}/history` : timeline des
modifications du projet **et de ses charges** (`GET /projects/{id}/history`, jointure change_log
sur `projects` + `monthly_loads` du projet). Lecture Lecteur+. L'UI masque les colonnes dérivées
(`last_update`, `total_project_load`, `updated_at`) pour ne montrer que les actions métier.
⚠️ Les **project_id ne sont jamais réutilisés** (même après suppression) — `generate_project_id`
exclut aussi les ids présents dans `change_log`, sinon un nouveau projet hériterait d'un historique.

### Drill-down par projet (§5.3 + §5.5)
Sur **Charge équipe** ET **Taux d'occupation**, chaque équipe a un **chevron** : déplier charge à
la demande le détail par projet (`GET /dashboards/team-load/detail?team=&start=`, partagé) — un
projet par sous-ligne, charge (jours) par mois, lien vers la grille de saisie. La somme du détail
= la charge agrégée (= numérateur du taux). NB : encoder le nom d'équipe (`encodeURIComponent`),
certains contiennent `&`.

### Gestion des équipes (§3.3, Admin)
Onglet **Équipes** visible aux seuls Admin : table + création/édition/suppression (`TeamsPage`).
API : `POST /teams`, `PUT /teams/{name}` (nom immuable, FK), `DELETE /teams/{name}` (refus 409 si
l'équipe est encore référencée par des charges/capacités). Écritures journalisées (§8.2).

### Concurrence (objectif n°1)
La grille de saisie n'envoie **que les cellules modifiées** : deux utilisateurs éditant des
cellules différentes du même projet ne s'écrasent pas.
**Verrouillage optimiste** : `GET /projects/{id}/loads` renvoie l'`updated_at` de chaque cellule ;
le client le renvoie comme `base_updated_at` à la sauvegarde. Si une cellule a changé entre-temps,
`PUT` répond **409** avec le détail des conflits (valeur serveur vs valeur saisie) et **n'écrit
rien** (tout ou rien). Le front affiche un bandeau de conflit (« Écraser » / « Garder le serveur »),
surligne en orange les cellules modifiées par un collègue pendant l'édition, et **rafraîchit la
grille toutes les 15 s** (`refetchInterval`) pour voir les saisies des autres en quasi temps réel.
Couvert par `test_load_save_optimistic_conflict`.

## État par lot
| Lot | Périmètre | État |
|---|---|---|
| 1 | Socle données : schéma 4 tables + migration Alembic + `migrate_from_xlsm.py` + tests §6.1/§6.2 | ✅ **fait — schéma validé** |
| 2 | API CRUD + calculs §6 (3/4/7/8) + QC §7 + dashboards 5.3–5.8 calculables via API (tests) | ✅ **fait** (64 tests verts, non-régression OK) |
| 3 | Front portefeuille + saisie (5.1/5.2) | ✅ **fait** (React/TS/Vite ; build OK ; concurrence démontrée) |
| 4 | Front dashboards (5.3–5.8) + navigation | ✅ **fait** (6 écrans + barre d'onglets + Recharts ; build OK) |
| 5 | Auth JWT + 3 rôles + audit `change_log` + sauvegarde/restauration | ✅ **fait** (76 tests verts) |

**Les 5 lots de la spec sont livrés.**

> Lot 2 expose : `/referentials`, `/teams`, `/projects` (CRUD + QC), `/projects/{id}/loads`
> (grille §5.2), `/capacity` (pivot + upsert §6.7), `/dashboards/{team-load,occupancy,
> overloads,roadmap,prioritization}`. Auth/rôles ouverts (→ Lot 5).

> **Non-régression métier (§9) validée** : `Charge équipe` et `Capa équipe` recalculés
> correspondent **cellule par cellule** aux onglets du classeur (63 équipes, 756 cellules,
> 0 écart) sur le mois de référence du classeur (2026-05).

## Règles arrêtées (ne pas réinterpréter)
- §6.5 Jours ouvrés = lundi→vendredi, **fériés inclus** (aucun calcul de fériés).
- §6.7 Capa projet : seul le terme `Jours_Indispo` est pondéré par la part projet.
- Référentiels §4 : valeurs reprises **à l'identique**.

## Lancer les tests
```bash
cd backend
python -m pytest -q          # SQLite en mémoire, aucune dépendance externe
```

## Décisions d'implémentation (Lot 1)
- Référentiels §4 stockés comme **colonnes texte** validées au niveau service/Pydantic contre les
  listes de `app/enums.py` (pas d'`ENUM` SQL figé) → édition admin possible en Lot 5 sans migration.
- `in_plan`, `last_update`, `total_project_load` sont **recalculés** par l'app, jamais saisis.
  À l'import, on stocke un **snapshot fidèle** du classeur (pour le test de non-régression §9),
  puis l'app recalcule à chaque écriture.
- Équipes orphelines (référencées dans les charges/capa mais absentes de l'onglet `Equipes`) :
  créées en **stub** à l'import et **signalées** dans le rapport, pour ne perdre aucune donnée.
- Validation des **référentiels §4 = à la saisie uniquement** (create/update), pas en restitution :
  les données migrées contiennent des valeurs legacy hors référentiel qui doivent rester lisibles.
- `Taux Occupation` du classeur est **périmé** (dénominateur recalculé à un autre instant que la
  capacité) : l'app recalcule le taux de façon cohérente → on n'aligne PAS le test dessus.

## ⚠️ Point ouvert à trancher (signalé, non deviné — cf. §11)
- **Référentiel PROGRAMME (§4)** : la spec liste `LOCAL/GLOBAL/Chronique/MB/ORSEC`, mais la colonne
  réelle contient ~12 autres valeurs (`ARCHI`, `MFT`, `Modern BI`, `NETWORK`…). Soit la liste §4
  est à corriger, soit la colonne est en texte libre. En attendant : import non bloquant + warning.
- **`Vite==>Pas Cher`** (data) vs **`Vite ==> Pas Cher`** (§4) : variante d'espaces à normaliser ?
