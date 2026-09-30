import type { SVGProps } from "react";

// Собственные глифы «Бюро» (strigov-crm Ico): viewBox 14×14, stroke 1.4.
export type IcoProps = SVGProps<SVGSVGElement> & { size?: number };

const svg = ({ size = 14, ...rest }: IcoProps) => ({
  width: size,
  height: size,
  viewBox: "0 0 14 14",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.4,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  ...rest,
});

export const Ico = {
  search: (p: IcoProps) => <svg {...svg(p)}><circle cx="6" cy="6" r="4" /><line x1="9" y1="9" x2="13" y2="13" /></svg>,
  plus: (p: IcoProps) => <svg {...svg(p)}><line x1="7" y1="1" x2="7" y2="13" /><line x1="1" y1="7" x2="13" y2="7" /></svg>,
  sun: (p: IcoProps) => <svg {...svg(p)}><circle cx="7" cy="7" r="2.5" /><line x1="7" y1="1" x2="7" y2="2.5" /><line x1="7" y1="11.5" x2="7" y2="13" /><line x1="1" y1="7" x2="2.5" y2="7" /><line x1="11.5" y1="7" x2="13" y2="7" /><line x1="2.93" y1="2.93" x2="4.05" y2="4.05" /><line x1="9.95" y1="9.95" x2="11.07" y2="11.07" /><line x1="11.07" y1="2.93" x2="9.95" y2="4.05" /><line x1="4.05" y1="9.95" x2="2.93" y2="11.07" /></svg>,
  moon: (p: IcoProps) => <svg {...svg(p)}><path d="M11 8.5A4.5 4.5 0 0 1 5.5 3a4.5 4.5 0 1 0 5.5 5.5z" /></svg>,
  "chevron-right": (p: IcoProps) => <svg {...svg(p)}><polyline points="5,2 10,7 5,12" /></svg>,
  x: (p: IcoProps) => <svg {...svg(p)}><line x1="2" y1="2" x2="12" y2="12" /><line x1="12" y1="2" x2="2" y2="12" /></svg>,
} as const;

export type IcoName = keyof typeof Ico;
