import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { pilierColor } from "../dash";
import type { RoadmapItem } from "../types";
import ExportButton from "../components/ExportButton";

const DAY = 86_400_000;

export default function RoadmapPage() {
  const q = useQuery({ queryKey: ["roadmap"], queryFn: api.roadmap });

  const model = useMemo(() => {
    const items = (q.data ?? []).filter((p) => p.start_date && p.end_date);
    if (!items.length) return null;
    const starts = items.map((p) => +new Date(p.start_date!));
    const ends = items.map((p) => +new Date(p.end_date!));
    const min = Math.min(...starts);
    const max = Math.max(...ends);
    const span = Math.max(max - min, DAY);
    // Graduations annuelles.
    const ticks: { left: number; label: string }[] = [];
    const d = new Date(min);
    d.setMonth(0, 1);
    for (let y = d.getFullYear(); +new Date(y, 0, 1) <= max; y++) {
      ticks.push({ left: ((+new Date(y, 0, 1) - min) / span) * 100, label: String(y) });
    }
    const piliers = [...new Set(items.map((p) => p.pilier_strategique ?? "—"))];
    return { items, min, span, ticks, piliers };
  }, [q.data]);

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;
  if (!model) return <p className="muted">Aucun projet in plan avec dates de début et de fin.</p>;

  const undated = (q.data ?? []).length - model.items.length;
  const pos = (p: RoadmapItem) => {
    const s = +new Date(p.start_date!);
    const e = +new Date(p.end_date!);
    return { left: ((s - model.min) / model.span) * 100, width: ((e - s) / model.span) * 100 };
  };

  return (
    <div>
      <h2>Roadmap (§5.7)</h2>
      <div className="toolbar">
        <span className="muted">
          Projets <strong>in plan</strong> sur leur période, couleur par pilier stratégique.
          {undated > 0 && ` ${undated} projet(s) sans dates complètes non affichés.`}
        </span>
        <ExportButton
          name="roadmap"
          headers={["Project ID", "Projet", "Pilier stratégique", "Début", "Fin"]}
          rows={(q.data ?? []).map((p) => [
            p.project_id, p.project_name, p.pilier_strategique ?? "", p.start_date ?? "", p.end_date ?? "",
          ])}
        />
      </div>

      <div className="legend">
        {model.piliers.map((pl) => (
          <span key={pl} style={{ background: pilierColor(pl === "—" ? null : pl), color: "#fff" }}>
            {pl}
          </span>
        ))}
      </div>

      <div className="gantt">
        <div className="gantt-head">
          <div className="gantt-label" />
          <div className="gantt-track">
            {model.ticks.map((t) => (
              <div key={t.label} className="gantt-tick" style={{ left: `${t.left}%` }}>
                <span>{t.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="gantt-body">
          {model.items.map((p) => {
            const { left, width } = pos(p);
            return (
              <div className="gantt-row" key={p.project_id}>
                <div className="gantt-label" title={p.project_name}>
                  {p.project_name}
                </div>
                <div className="gantt-track">
                  {model.ticks.map((t) => (
                    <div key={t.label} className="gantt-grid" style={{ left: `${t.left}%` }} />
                  ))}
                  <div
                    className="gantt-bar"
                    style={{
                      left: `${left}%`,
                      width: `${Math.max(width, 0.5)}%`,
                      background: pilierColor(p.pilier_strategique),
                    }}
                    title={`${p.project_id} — ${p.project_name}\n${p.start_date} → ${p.end_date}\n${p.pilier_strategique ?? "—"}`}
                  >
                    <span>{p.project_id}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
