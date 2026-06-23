import { exportCsv, dateStamp } from "../csv";

interface Props {
  /** Base du nom de fichier ; un horodatage AAAA-MM-JJ et .csv sont ajoutés. */
  name: string;
  headers: string[];
  rows: (string | number | null | undefined)[][];
  disabled?: boolean;
}

export default function ExportButton({ name, headers, rows, disabled }: Props) {
  return (
    <button
      onClick={() => exportCsv(`${name}-${dateStamp()}`, headers, rows)}
      disabled={disabled || rows.length === 0}
      title="Exporter ce tableau au format CSV (Excel)"
    >
      ⤓ Exporter (CSV)
    </button>
  );
}
