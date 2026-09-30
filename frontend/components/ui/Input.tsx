import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const invalid = (value: unknown) => value === true || value === "true";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...rest }, ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-9 w-full rounded-sm border bg-bg px-3 text-sm text-ink placeholder:text-ink-2 transition-colors focus:border-line-strong disabled:opacity-60",
        invalid(rest["aria-invalid"]) ? "border-danger" : "border-line-c",
        className,
      )}
      {...rest}
    />
  );
});
