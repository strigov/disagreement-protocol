const MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
const MONTHS_SHORT = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

const pad = (value: number) => String(value).padStart(2, "0");

/** Дата по правилам «Бюро»: «Сегодня 16:05», «12 ноября 16:05», «12 ноя 2025 16:05». */
export function fmtDateTime(value: number | Date, now: Date = new Date()): string {
  const date = value instanceof Date ? value : new Date(value);
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  if (date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()) {
    return `Сегодня ${time}`;
  }
  if (date.getFullYear() === now.getFullYear()) return `${date.getDate()} ${MONTHS[date.getMonth()]} ${time}`;
  return `${date.getDate()} ${MONTHS_SHORT[date.getMonth()]} ${date.getFullYear()} ${time}`;
}
