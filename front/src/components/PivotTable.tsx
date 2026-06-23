import { monthShort } from "../dash";
import type { NumberPivot } from "../types";

interface Props {
  data: NumberPivot;
  /** N'afficher que les équipes ayant au moins une valeur non nulle. */
  hideEmpty?: boolean;
  decimals?: number;
  /** Si fourni, les cellules deviennent cliquables (édition). */
  onCellClick?: (team: string, month: string) => void;
}

export default function PivotTable({ data, hideEmpty = true, decimals = 1, onCellClick }: Props) {
  // En mode édition, on garde toutes les équipes (y compris celles à 0, pour pouvoir saisir).
  const rows = hideEmpty && !onCellClick
    ? data.rows.filter((r) => r.values.some((v) => v !== 0))
    : data.rows;
  const totals = data.months.map((_, i) => rows.reduce((s, r) => s + (r.values[i] ?? 0), 0));
  const fmt = (v: number) => (v === 0 ? "" : v.toFixed(decimals));

  return (
    <div className="table-wrap">
      <table className="pivot">
        <thead>
          <tr>
            <th className="sticky-col">Équipe</th>
            {data.months.map((m) => (
              <th key={m} style={{ textAlign: "right" }}>
                {monthShort(m)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.team}>
              <td className="sticky-col">{r.team}</td>
              {r.values.map((v, i) => (
                <td
                  key={i}
                  style={{ textAlign: "right" }}
                  className={onCellClick ? "editable" : undefined}
                  title={onCellClick ? "Cliquer pour éditer" : undefined}
                  onClick={onCellClick ? () => onCellClick(r.team, data.months[i]) : undefined}
                >
                  {fmt(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="sticky-col">
              <strong>Total</strong>
            </td>
            {totals.map((t, i) => (
              <td key={i} style={{ textAlign: "right" }}>
                <strong>{t.toFixed(decimals)}</strong>
              </td>
            ))}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
