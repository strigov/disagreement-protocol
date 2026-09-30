"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/icons/Icon";
import { IconButton } from "@/components/ui/Button";

const GAP = 4;
const VIEWPORT_MARGIN = 8;

/**
 * Меню действий строки. Поповер рендерится в body, чтобы прокручиваемый
 * контейнер таблицы его не обрезал. Удаление только запрашивается у родителя.
 */
export function RowActions({ disabled, onMergePrevious, onMergeNext, onRequestDelete }: {
  disabled: boolean;
  onMergePrevious: () => void;
  onMergeNext: () => void;
  onRequestDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const close = useCallback((restoreFocus: boolean) => {
    setOpen(false);
    setPosition(null);
    if (restoreFocus) trigger.current?.focus();
  }, []);

  useLayoutEffect(() => {
    if (!open || !trigger.current || !menu.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const own = menu.current.getBoundingClientRect();
    const below = anchor.bottom + GAP;
    const top = below + own.height > window.innerHeight - VIEWPORT_MARGIN && anchor.top - GAP - own.height > VIEWPORT_MARGIN
      ? anchor.top - GAP - own.height
      : below;
    const left = Math.min(Math.max(VIEWPORT_MARGIN, anchor.right - own.width), window.innerWidth - own.width - VIEWPORT_MARGIN);
    setPosition({ top, left: Math.max(VIEWPORT_MARGIN, left) });
  }, [open]);

  // Фокус переносится, когда поповер уже стоит на месте и видим.
  const placed = position !== null;
  useEffect(() => {
    if (!open || !placed) return;
    const items = menu.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
    (items?.[0] ?? menu.current)?.focus();
  }, [open, placed]);

  useEffect(() => {
    if (!open) return;
    const inside = (target: EventTarget | null) =>
      target instanceof Node && (!!menu.current?.contains(target) || !!trigger.current?.contains(target));
    const onPointerDown = (event: PointerEvent) => { if (!inside(event.target)) close(false); };
    const onScroll = (event: Event) => { if (!inside(event.target)) close(false); };
    const onResize = () => close(false);
    const onFocusIn = (event: FocusEvent) => { if (!inside(event.target)) close(false); };
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("scroll", onScroll, true);
    document.addEventListener("focusin", onFocusIn);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("scroll", onScroll, true);
      document.removeEventListener("focusin", onFocusIn);
      window.removeEventListener("resize", onResize);
    };
  }, [open, close]);

  const onMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"));
    if (!items.length) return;
    event.preventDefault();
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    const next = event.key === "Home" ? 0
      : event.key === "End" ? items.length - 1
        : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
    items[next]?.focus();
  };

  const choose = (action: () => void) => {
    close(true);
    action();
  };

  // После выбора фокус возвращается на кнопку меню (и на неё же — после диалога подтверждения).
  const item = (label: string, icon: IconName, action: () => void, danger = false) => (
    <button
      type="button"
      disabled={disabled}
      onClick={() => choose(action)}
      className={cn(
        "flex w-full items-center gap-2 rounded-xs px-2.5 py-2 text-left text-sm transition-colors hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-50",
        danger ? "text-danger" : "text-ink",
      )}
    >
      <Icon name={icon} className={danger ? "text-danger" : "text-ink-2"} />{label}
    </button>
  );

  return (
    <>
      <IconButton
        ref={trigger}
        icon="ellipsis"
        label="Действия со строкой"
        size="sm"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? close(false) : setOpen(true))}
      />
      {open && createPortal(
        <div
          ref={menu}
          id={menuId}
          tabIndex={-1}
          onKeyDown={onMenuKeyDown}
          style={position ? { top: position.top, left: position.left } : { top: 0, left: 0, visibility: "hidden" }}
          className="fixed z-50 w-row-menu rounded-md border border-line-c bg-bg-elev p-1 text-ink shadow-md focus-visible:outline-none"
        >
          {item("Объединить с предыдущей", "arrow-up", onMergePrevious)}
          {item("Объединить со следующей", "arrow-down", onMergeNext)}
          <div className="my-1 border-t border-line-c" />
          {item("Исключить из протокола", "trash", onRequestDelete, true)}
        </div>,
        document.body,
      )}
    </>
  );
}
