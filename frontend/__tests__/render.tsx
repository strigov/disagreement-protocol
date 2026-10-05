import { render as testingRender, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement, ReactNode } from "react";

function Router({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

export function render(ui: ReactElement, options?: RenderOptions) {
  return testingRender(ui, { wrapper: Router, ...options });
}
