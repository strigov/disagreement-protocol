import { createContext, useContext, type ReactNode } from "react";

const RouteContext = createContext({ id: "doc1" });
export const useTestParams = () => useContext(RouteContext);
export function TestRoute({ id, children }: { id: string; children: ReactNode }) {
  return <RouteContext.Provider value={{ id }}>{children}</RouteContext.Provider>;
}
