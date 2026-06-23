import { createContext, useContext, useState, type ReactNode } from "react";
import { firstOfCurrentMonth } from "./dash";

interface WindowCtx {
  start: string; // "YYYY-MM-01"
  setStart: (s: string) => void;
}

const Ctx = createContext<WindowCtx | null>(null);

export function WindowProvider({ children }: { children: ReactNode }) {
  const [start, setStart] = useState<string>(firstOfCurrentMonth());
  return <Ctx.Provider value={{ start, setStart }}>{children}</Ctx.Provider>;
}

export function useWindowStart(): WindowCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useWindowStart hors WindowProvider");
  return ctx;
}
