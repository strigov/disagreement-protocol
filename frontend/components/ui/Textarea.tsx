import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const invalid = (value: unknown) => value === true || value === "true";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, ...rest }, ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full resize-y rounded-sm border bg-bg px-3 py-2 text-sm leading-relaxed text-ink placeholder:text-ink-2 transition-colors focus:border-line-strong disabled:opacity-60",
        invalid(rest["aria-invalid"]) ? "border-danger" : "border-line-c",
        className,
      )}
      {...rest}
    />
  );
});
