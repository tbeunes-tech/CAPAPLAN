import type { CSSProperties } from "react";
import type { ColorName } from "./types";

export function monthShort(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { month: "short", year: "2-digit" });
}

export function firstOfCurrentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

// Code couleur §5.5 (vert <80 % / ambre 80–100 % / rouge >100 % / marqueur capacité nulle).
export const COLOR_STYLE: Record<ColorName, CSSProperties> = {
  green: { background: "#e4f3ea", color: "#1f7a44" },
  amber: { background: "#fdf0d5", color: "#9c6500" },
  red: { background: "#fbe2e2", color: "#b32525" },
  overload_null_capacity: {
    background:
      "repeating-linear-gradient(45deg,#f3c0c0,#f3c0c0 5px,#e9a8a8 5px,#e9a8a8 10px)",
    color: "#7a1414",
    fontWeight: 700,
  },
};

export function rateLabel(rate: number, color: ColorName): string {
  if (color === "overload_null_capacity") return "∞";
  return `${Math.round(rate * 100)}%`;
}

// Couleur stable par pilier stratégique (roadmap §5.7).
const PILIER_COLORS = [
  "#2f6df6", "#1f9d55", "#d98c00", "#9b51e0", "#e0518a", "#0fb5ba", "#d23b3b",
];
export function pilierColor(pilier: string | null): string {
  if (!pilier) return "#8a91a0";
  let h = 0;
  for (let i = 0; i < pilier.length; i++) h = (h * 31 + pilier.charCodeAt(i)) >>> 0;
  return PILIER_COLORS[h % PILIER_COLORS.length];
}
