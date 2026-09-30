export type ClassValue = string | false | null | undefined;

// Склейка классов без зависимостей. Конфликты не разрешаются: вызывающая сторона
// не переопределяет свойства примитива через className, для отличий есть props.
export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
