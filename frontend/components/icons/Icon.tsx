import {
  ArrowDown, ArrowLeft, ArrowLeftRight, ArrowRight, ArrowUp, ArrowUpRight, Check, CheckCheck, ChevronDown, ChevronLeft,
  CircleAlert, CircleCheck, Download, Ellipsis, FileText, FileUp, Info, LoaderCircle, LockKeyhole,
  Monitor, RotateCcwClock, Table2, TextAlignStart, Trash, TriangleAlert, type LucideIcon,
} from "lucide-react";
import { Ico, type IcoName } from "./Ico";
import { cn } from "@/lib/cn";

// Явный реестр вместо `import * as lucide`: в бандл попадают только эти иконки.
const LUCIDE = {
  "align-left": TextAlignStart,
  "arrow-down": ArrowDown,
  "arrow-left": ArrowLeft,
  "arrow-left-right": ArrowLeftRight,
  "arrow-right": ArrowRight,
  "arrow-up": ArrowUp,
  "arrow-up-right": ArrowUpRight,
  check: Check,
  "check-check": CheckCheck,
  "chevron-down": ChevronDown,
  "chevron-left": ChevronLeft,
  "circle-alert": CircleAlert,
  "circle-check": CircleCheck,
  download: Download,
  ellipsis: Ellipsis,
  "file-text": FileText,
  "file-up": FileUp,
  history: RotateCcwClock,
  info: Info,
  "loader-circle": LoaderCircle,
  "lock-keyhole": LockKeyhole,
  monitor: Monitor,
  "table-2": Table2,
  trash: Trash,
  "triangle-alert": TriangleAlert,
} satisfies Record<string, LucideIcon>;

export type LucideIconName = keyof typeof LUCIDE;
export type IconName = IcoName | LucideIconName;

export interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  /** Доступное имя; без него иконка декоративная и скрыта от скринридеров. */
  label?: string;
}

export function Icon({ name, size = 14, className, label }: IconProps) {
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true as const };
  const classes = cn("shrink-0", className);
  if (name in Ico) {
    const Glyph = Ico[name as IcoName];
    return <Glyph size={size} className={classes} {...a11y} />;
  }
  const Lucide = LUCIDE[name as LucideIconName];
  return <Lucide size={size} strokeWidth={1.4} absoluteStrokeWidth className={classes} {...a11y} />;
}
