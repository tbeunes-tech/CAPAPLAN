# Brief Codex — Refonte du portefeuille projets DSI en application web

> Spécification fonctionnelle complète. Voir le fichier d'origine pour le contexte exhaustif.
> Ce dépôt implémente la spec par **lots** (§10). État courant : **Lot 1 — Socle données**.

Le contenu intégral de la spec est conservé dans ce fichier (référence de vérité métier).
Les règles de gestion verrouillées par des tests sont au §6, le modèle de données au §3,
la migration au §9. Se reporter à `AGENTS.md` pour l'état d'avancement par lot.

---

## 3. Modèle de données (4 tables persistées)

- `projects` — portefeuille. `project_id` (PK, immuable, `yymm-NNNN`), `entite`, `domain_lead`,
  `project_name`, `project_leader`, `status`, `priorite`, `pilier_strategique`, `budget_item`,
  `budget_owner`, `programme`, `in_plan` (**calculé** §6.2), `start_date`, `end_date`,
  `last_update` (**calculé** §6.6), `total_project_load` (**calculé**, somme des charges).
- `monthly_loads` — table de faits. `(project_id, team, month)` unique. `days`, `in_plan` (dénormalisé), `updated_at`.
- `teams` — `name` (PK), `manager`, `capacite_etp`, `description`.
- `monthly_capacity` — `(team, month)` unique. `etp_team`, `etp_projet`, `part_projet`,
  `jours_indispo`, `capa_projet` (§6.7), `updated_at`.

Les restitutions (§5.3–5.8) sont **calculées à la volée**, jamais stockées.

## 4. Référentiels

- **ENTITE :** CPM · DEPOTRADE · IVRYLAB · OCP FORMATION · OCP RETAIL · PHV · PHR · PHX FR GLOBAL · PHX FR RETAIL · PHX GROUP · PHOENIX OCP
- **DOMAIN LEAD :** ETU-BI · ETU-LEG · ETU-CUST EXP · ETU-GAIN · ETU-SAP · CYBER SEC · TP · TP-OPE · TP-PM · ETU-PPF · AUTRE
- **PILIER STRATEGIQUE :** Supply Chain efficiente · Push ==> Pull · Vite ==> Pas Cher · Renforcement SI · Autres projets business stratégiques · Projets groupe
- **PRIORITE :** P0 · P1 · P2 · P3
- **STATUT :** In Progress · Scheduled · Closed · Not Scheduled · Canceled · On Hold
- **PROGRAMME :** LOCAL · GLOBAL · Chronique · MB · ORSEC

## 6. Règles de gestion (couvertes par tests)

- **6.1 Project ID** — `yymm-NNNN`, compteur global séquentiel 4 chiffres, unique, immuable.
- **6.2 In Plan** — `true` si `status ∈ {In Progress, Scheduled}` (compat FR : En cours / Planifié).
- **6.3 Charge équipe** — fenêtre 12 mois, somme `days` où `in_plan`, arrondi 0,1.
- **6.4 Taux d'occupation** — `charge/capa` ; sentinelle `-1` si charge>0 & capa=0 ; sinon 0.
- **6.5 Jours ouvrés** — lundi→vendredi, **fériés INCLUS** (pas d'exclusion de fériés).
- **6.6 Last Update** — `max(monthly_loads.updated_at)` du projet.
- **6.7 Capa projet** — `MAX(0 ; ETP_Projet × JoursOuvrés − (ETP_Projet/ETP_Team) × Jours_Indispo)`.
- **6.8 Scénarios priorisation** — P0 / P0+P1(Renforcement SI) / P0+P1 / Plan intégral.

> ⚠️ §6.7 : seul le terme d'indisponibilité est pondéré par la part projet. Le commentaire
> d'en-tête VBA est erroné — ne pas le suivre. Formule vérifiée contre les données du classeur.

## 7. Contrôle qualité (sur `in_plan = true`)

Date Error · Status Error · Obsolete forecast (≥31 j) · Leader Error.

## 9. Migration (`scripts/migrate_from_xlsm.py`)

- `projects` ← `Project Portfolio 25-26` (col A→O).
- `monthly_loads` ← `Détail Mensuel` (normaliser `InPlan` : VRAI/TRUE/OUI/YES → true).
- `teams` ← `Equipes`.
- `monthly_capacity` ← `Détail Capa Mensuelle`.

## 10. Lots

1. **Socle données** (CE LOT) — schéma + migration + import + tests §6.1/§6.2.
2. API + règles §6 + QC §7.
3. Front portefeuille + saisie (5.1/5.2).
4. Dashboards (5.3–5.8).
5. Auth, rôles, historisation, sauvegarde/restauration.
