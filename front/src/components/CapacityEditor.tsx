import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { monthShort } from "../dash";

/** Jours ouvrés lun→ven du mois (fériés inclus, §6.5) — pour l'aperçu de capa_projet. */
function workingDays(monthIso: string): number {
  const d = new Date(monthIso);
  const y = d.getFullYear();
  const m = d.getMonth();
  const days = new Date(y, m + 1, 0).getDate();
  let n = 0;
  for (let day = 1; day <= days; day++) {
    const wd = new Date(y, m, day).getDay();
    if (wd !== 0 && wd !== 6) n++;
  }
  return n;
}

/** §6.7 — aperçu client (le serveur fait foi à l'enregistrement). */
function previewCapa(etpProjet: number, etpTeam: number, wd: number, indispo: number): number {
  const part = etpTeam ? etpProjet / etpTeam : 0;
  return Math.max(0, etpProjet * wd - part * indispo);
}

interface Props {
  team: string;
  month: string;
  onClose: () => void;
}

export default function CapacityEditor({ team, month, onClose }: Props) {
  const qc = useQueryClient();
  const cellQ = useQuery({
    queryKey: ["capacity-cell", team, month],
    queryFn: () => api.capacityCell(team, month),
  });

  const [etpTeam, setEtpTeam] = useState<string>("");
  const [etpProjet, setEtpProjet] = useState<string>("");
  const [indispo, setIndispo] = useState<string>("");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pré-remplissage une fois la cellule chargée.
  if (cellQ.data && !loaded) {
    setEtpTeam(cellQ.data.etp_team?.toString() ?? "");
    setEtpProjet(cellQ.data.etp_projet?.toString() ?? "");
    setIndispo(cellQ.data.jours_indispo?.toString() ?? "0");
    setLoaded(true);
  }

  const wd = workingDays(month);
  const nTeam = Number(etpTeam) || 0;
  const nProjet = Number(etpProjet) || 0;
  const nIndispo = Number(indispo) || 0;
  const capaPreview = previewCapa(nProjet, nTeam, wd, nIndispo);

  const save = useMutation({
    mutationFn: () =>
      api.saveCapacity({
        team,
        month,
        etp_team: etpTeam === "" ? null : nTeam,
        etp_projet: etpProjet === "" ? null : nProjet,
        jours_indispo: indispo === "" ? null : nIndispo,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["capacity"] });
      qc.invalidateQueries({ queryKey: ["occupancy"] });
      qc.invalidateQueries({ queryKey: ["overloads"] });
      qc.invalidateQueries({ queryKey: ["prioritization"] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" style={{ width: 440 }} onClick={(e) => e.stopPropagation()}>
        <h2>
          Capacité — {team} · {monthShort(month)}
        </h2>
        <p className="muted">
          Éditez les entrées ; <code>capa_projet</code> est recalculée (§6.7). Jours ouvrés du mois
          (lun→ven, fériés inclus) : <strong>{wd}</strong>.
        </p>
        {cellQ.isLoading ? (
          <p>Chargement…</p>
        ) : (
          <>
            <div className="form-grid">
              <div className="field">
                <label>ETP équipe</label>
                <input type="number" step="0.1" min="0" value={etpTeam}
                  onChange={(e) => setEtpTeam(e.target.value)} />
              </div>
              <div className="field">
                <label>ETP dédié projet</label>
                <input type="number" step="0.1" min="0" value={etpProjet}
                  onChange={(e) => setEtpProjet(e.target.value)} />
              </div>
              <div className="field">
                <label>Jours d'indisponibilité</label>
                <input type="number" step="0.5" min="0" value={indispo}
                  onChange={(e) => setIndispo(e.target.value)} />
              </div>
              <div className="field">
                <label>Part projet (calculée)</label>
                <input value={nTeam ? (nProjet / nTeam).toFixed(2) : "0"} disabled />
              </div>
            </div>
            <div className="banner ok" style={{ marginTop: 14 }}>
              capa_projet ={" "}
              <strong>
                max(0 ; {nProjet} × {wd} − {nTeam ? (nProjet / nTeam).toFixed(2) : 0} × {nIndispo}) ={" "}
                {capaPreview.toFixed(1)} j
              </strong>
            </div>
            {error && <p className="err">⚠ {error}</p>}
            <div className="modal-actions">
              <button onClick={onClose}>Annuler</button>
              <button className="primary" disabled={save.isPending} onClick={() => { setError(null); save.mutate(); }}>
                {save.isPending ? "Enregistrement…" : "Enregistrer"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
