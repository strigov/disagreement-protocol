import { fmtDateTime } from "@/lib/format";

// Дата «сейчас» фиксирована, чтобы тест не зависел от календаря.
const NOW = new Date(2026, 8, 30, 18, 30);

test("same day is shown as «Сегодня» with a zero-padded time", () => {
  expect(fmtDateTime(new Date(2026, 8, 30, 9, 5), NOW)).toBe("Сегодня 09:05");
  expect(fmtDateTime(new Date(2026, 8, 30, 0, 0), NOW)).toBe("Сегодня 00:00");
});

test("same year uses the genitive month name", () => {
  expect(fmtDateTime(new Date(2026, 10, 12, 16, 5), NOW)).toBe("12 ноября 16:05");
  expect(fmtDateTime(new Date(2026, 0, 1, 7, 0), NOW)).toBe("1 января 07:00");
  expect(fmtDateTime(new Date(2026, 8, 29, 23, 59), NOW)).toBe("29 сентября 23:59");
});

test("another year uses the short month and the year", () => {
  expect(fmtDateTime(new Date(2025, 10, 12, 16, 5), NOW)).toBe("12 ноя 2025 16:05");
  expect(fmtDateTime(new Date(2024, 4, 3, 8, 9), NOW)).toBe("3 мая 2024 08:09");
});

test("the same calendar day of another month or year is not «Сегодня»", () => {
  expect(fmtDateTime(new Date(2026, 7, 30, 10, 0), NOW)).toBe("30 августа 10:00");
  expect(fmtDateTime(new Date(2025, 8, 30, 10, 0), NOW)).toBe("30 сен 2025 10:00");
});

test("accepts a timestamp as well as a Date", () => {
  expect(fmtDateTime(new Date(2026, 8, 30, 9, 5).getTime(), NOW)).toBe("Сегодня 09:05");
});

test("names every month", () => {
  const long = Array.from({ length: 12 }, (_, month) => fmtDateTime(new Date(2026, month, 15, 12, 0), new Date(2026, 5, 1)));
  expect(long.map((label) => label.split(" ")[1])).toEqual([
    "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря",
  ]);
  const short = Array.from({ length: 12 }, (_, month) => fmtDateTime(new Date(2025, month, 15, 12, 0), NOW));
  expect(short.map((label) => label.split(" ")[1])).toEqual([
    "янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек",
  ]);
});
