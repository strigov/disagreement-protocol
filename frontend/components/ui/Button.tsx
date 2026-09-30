import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/icons/Icon";

export type ButtonVariant = "primary" | "ghost" | "outline" | "danger";
export type ButtonSize = "xs" | "sm" | "md";

const BASE = "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const SIZES: Record<ButtonSize, string> = {
  xs: "h-7 px-2 text-xs",
  sm: "h-8 px-2.5 text-sm",
  md: "h-9 px-3 text-sm",
};

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-ink hover:opacity-90",
  ghost: "border border-line-strong bg-transparent text-ink-1 hover:bg-bg-hover hover:text-ink",
  outline: "border border-line-c bg-bg text-ink-1 hover:bg-bg-hover hover:text-ink",
  danger: "bg-danger-soft text-danger hover:bg-bg-hover",
};

/** Классы кнопки для <Link>/<label>, которые выглядят как кнопки. */
export function buttonClassName({ variant, size = "md", className }: { variant: ButtonVariant; size?: ButtonSize; className?: string }) {
  return cn(BASE, SIZES[size], VARIANTS[variant], className);
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant: ButtonVariant; size?: ButtonSize };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, className, type = "button", ...rest }, ref,
) {
  return <button ref={ref} type={type} className={buttonClassName({ variant, size, className })} {...rest} />;
});

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  icon: IconName;
  label: string;
  size?: "sm" | "md";
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, label, size = "md", className, type = "button", ...rest }, ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-grid shrink-0 place-items-center rounded-sm text-ink-2 transition-colors hover:bg-bg-hover hover:text-ink aria-expanded:bg-bg-active aria-expanded:text-ink disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "h-8 w-8" : "h-9 w-9",
        className,
      )}
      {...rest}
    >
      <Icon name={icon} size={16} />
    </button>
  );
});
