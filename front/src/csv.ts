/** Export CSV compatible Excel FR : séparateur ';' + BOM UTF-8 (accents préservés). */
type Cell = string | number | null | undefined;

function escape(v: Cell): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  return /[;"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCsv(filename: string, headers: string[], rows: Cell[][]): void {
  const lines = [headers, ...rows].map((r) => r.map(escape).join(";"));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Suffixe horodaté lisible pour les noms de fichiers, ex. 2026-06-23. */
export function dateStamp(): string {
  return new Date().toISOString().slice(0, 10);
}
