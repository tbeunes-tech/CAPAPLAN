import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { pilierColor } from "../dash";
import type { RoadmapItem } from "../types";
import ExportButton from "../components/ExportButton";

const DAY = 86_400_000;
const distinct = (vals: (string | null)[]) =>
  [...new Set(vals.filter((v): v is string => !!v))].sort();

export default function RoadmapPage() {
  const q = useQuery({ queryKey: ["roadmap"], queryFn: api.roadmap });
  const [pilier, setPilier] = useState("");
  const [prio, setPrio] = useState("");
  const [prioDsi, setPrioDsi] = useState("");

  const model = useMemo(() => {
    const items = (q.data ?? []).filter((p) => p.start_date && p.end_date);
    if (!items.length) return null;
    const min = Math.min(...items.map((p) => +new Date(p.start_date!)));
    const max = Math.max(...items.map((p) => +new Date(p.end_date!)));
    const span = Math.max(max - min, DAY);
    const ticks: { left: number; label: string }[] = [];
    for (let y = new Date(min).getFullYear(); +new Date(y, 0, 1) <= max; y++) {
      ticks.push({ left: ((+new Date(y, 0, 1) - min) / span) * 100, label: String(y) });
    }
    return {
      items, min, span, ticks,
      piliers: distinct(items.map((p) => p.pilier_strategique)),
      prios: distinct(items.map((p) => p.priorite)),
      priosDsi: distinct(items.map((p) => p.prio_dsi)),
    };
  }, [q.data]);

  if (q.isLoading) return <p>Chargement…</p>;
  if (q.isError) return <p className="err">Erreur : {(q.error as Error).message}</p>;
  if (!model) return <p className="muted">Aucun projet in plan avec dates de début et de fin.</p>;

  const visible = model.items.filter(
    (p) =>
      (!pilier || p.pilier_strategique === pilier) &&
      (!prio || p.priorite === prio) &&
      (!prioDsi || p.prio_dsi === prioDsi),
  );
  const pos = (p: RoadmapItem) => {
    const s = +new Date(p.start_date!);
    const e = +new Date(p.end_date!);
    return { left: ((s - model.min) / model.span) * 100, width: ((e - s) / model.span) * 100 };
  };

  return (
    <div>
      <h2>Roadmap (§5.7)</h2>
      <div className="toolbar">
        <label>Pilier&nbsp;
          <select value={pilier} onChange={(e) => setPilier(e.target.value)}>
            <option value="">tous</option>
            {model.piliers.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label>Prio&nbsp;
          <select value={prio} onChange={(e) => setPrio(e.target.value)}>
            <option value="">toutes</option>
            {model.prios.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label>Prio DSI&nbsp;
          <select value={prioDsi} onChange={(e) => setPrioDsi(e.target.value)}>
            <option value="">toutes</option>
            {model.priosDsi.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        {(pilier || prio || prioDsi) && (
          <button onClick={() => { setPilier(""); setPrio(""); setPrioDsi(""); }}>Réinitialiser</button>
        )}
        <span className="muted">{visible.length} / {model.items.length} projet(s)</span>
        <ExportButton
          name="roadmap"
          headers={["Project ID", "Projet", "Pilier", "Prio", "Prio DSI", "Début", "Fin"]}
          rows={visible.map((p) => [
            p.project_id, p.project_name, p.pilier_strategique ?? "", p.priorite ?? "",
            p.prio_dsi ?? "", p.start_date ?? "", p.end_date ?? "",
          ])}
        />
      </div>

      <div className="legend">
        {model.piliers.map((pl) => (
          <span key={pl} style={{ background: pilierColor(pl), color: "#fff" }}>{pl}</span>
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
          {visible.length === 0 ? (
            <p className="muted" style={{ padding: 10 }}>Aucun projet ne correspond aux filtres.</p>
          ) : (
            visible.map((p) => {
              const { left, width } = pos(p);
              return (
                <div className="gantt-row" key={p.project_id}>
                  <div className="gantt-label" title={`${p.project_id} — ${p.project_name}`}>
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
                      title={`${p.project_id} — ${p.project_name}\n${p.start_date} → ${p.end_date}\nPilier : ${p.pilier_strategique ?? "—"} · Prio : ${p.priorite ?? "—"} · Prio DSI : ${p.prio_dsi ?? "—"}`}
                    >
                      <span>{p.project_name}</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
