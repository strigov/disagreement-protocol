import {
  RECENT_DOCUMENTS_KEY,
  RECENT_DOCUMENTS_LIMIT,
  forgetDocument,
  readRecentDocuments,
  rememberDocument,
  type RecentDocument,
} from "@/lib/recent-documents";

const stored = () => JSON.parse(window.localStorage.getItem(RECENT_DOCUMENTS_KEY) ?? "null");
const seed = (value: unknown) => window.localStorage.setItem(RECENT_DOCUMENTS_KEY, JSON.stringify(value));

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("an empty or missing store reads as an empty list", () => {
  expect(readRecentDocuments()).toEqual([]);
});

test("remember then read returns the entry", () => {
  rememberDocument({ id: "a", title: "Договор аренды", stage: "analysis" }, 100);
  expect(readRecentDocuments()).toEqual([{ id: "a", title: "Договор аренды", stage: "analysis", openedAt: 100 }]);
  expect(stored()).toEqual([{ id: "a", title: "Договор аренды", stage: "analysis", openedAt: 100 }]);
});

test("uses the current time when none is given", () => {
  vi.spyOn(Date, "now").mockReturnValue(4242);
  rememberDocument({ id: "a", stage: "analysis" });
  expect(readRecentDocuments()[0].openedAt).toBe(4242);
});

test("entries are sorted from newest to oldest", () => {
  rememberDocument({ id: "old", title: "Старый", stage: "analysis" }, 10);
  rememberDocument({ id: "new", title: "Новый", stage: "parties" }, 30);
  rememberDocument({ id: "mid", title: "Средний", stage: "protocol" }, 20);
  expect(readRecentDocuments().map((item) => item.id)).toEqual(["new", "mid", "old"]);
});

test("read sorts a store that was written out of order", () => {
  seed([
    { id: "a", title: null, stage: "analysis", openedAt: 1 },
    { id: "b", title: null, stage: "analysis", openedAt: 3 },
    { id: "c", title: null, stage: "analysis", openedAt: 2 },
  ]);
  expect(readRecentDocuments().map((item) => item.id)).toEqual(["b", "c", "a"]);
});

test("remembering an existing id updates it in place and moves it to the top", () => {
  rememberDocument({ id: "a", title: "Первый", stage: "analysis" }, 10);
  rememberDocument({ id: "b", title: "Второй", stage: "analysis" }, 20);
  rememberDocument({ id: "a", title: "Первый", stage: "parties" }, 30);
  expect(readRecentDocuments()).toEqual([
    { id: "a", title: "Первый", stage: "parties", openedAt: 30 },
    { id: "b", title: "Второй", stage: "analysis", openedAt: 20 },
  ]);
});

test("a null, missing or blank title does not overwrite a previous non-empty one", () => {
  rememberDocument({ id: "a", title: "Договор", stage: "analysis" }, 10);
  rememberDocument({ id: "a", title: null, stage: "parties" }, 20);
  expect(readRecentDocuments()[0]).toMatchObject({ title: "Договор", stage: "parties", openedAt: 20 });
  rememberDocument({ id: "a", stage: "protocol" }, 30);
  expect(readRecentDocuments()[0]).toMatchObject({ title: "Договор", stage: "protocol" });
  rememberDocument({ id: "a", title: "   ", stage: "protocol" }, 40);
  expect(readRecentDocuments()[0]).toMatchObject({ title: "Договор" });
});

test("a new non-empty title replaces the old one", () => {
  rememberDocument({ id: "a", title: "Черновик", stage: "analysis" }, 10);
  rememberDocument({ id: "a", title: "Договор поставки", stage: "parties" }, 20);
  expect(readRecentDocuments()[0].title).toBe("Договор поставки");
});

test("an entry without any title is stored with a null title", () => {
  rememberDocument({ id: "a", stage: "analysis" }, 10);
  expect(readRecentDocuments()).toEqual([{ id: "a", title: null, stage: "analysis", openedAt: 10 }]);
});

test("the list is trimmed to the newest entries", () => {
  for (let i = 0; i < RECENT_DOCUMENTS_LIMIT + 3; i += 1) {
    rememberDocument({ id: `doc-${i}`, title: `Договор ${i}`, stage: "analysis" }, 1000 + i);
  }
  const ids = readRecentDocuments().map((item) => item.id);
  expect(ids).toHaveLength(RECENT_DOCUMENTS_LIMIT);
  expect(ids[0]).toBe(`doc-${RECENT_DOCUMENTS_LIMIT + 2}`);
  expect(ids).not.toContain("doc-0");
  expect(ids).not.toContain("doc-2");
  expect(ids).toContain("doc-3");
  expect(stored()).toHaveLength(RECENT_DOCUMENTS_LIMIT);
});

test("forget removes only that document from the list", () => {
  rememberDocument({ id: "a", title: "А", stage: "analysis" }, 10);
  rememberDocument({ id: "b", title: "Б", stage: "analysis" }, 20);
  forgetDocument("a");
  expect(readRecentDocuments().map((item) => item.id)).toEqual(["b"]);
  forgetDocument("missing");
  expect(readRecentDocuments().map((item) => item.id)).toEqual(["b"]);
});

test("invalid JSON reads as an empty list", () => {
  window.localStorage.setItem(RECENT_DOCUMENTS_KEY, "{not json");
  expect(readRecentDocuments()).toEqual([]);
});

test("a stored value that is not an array reads as an empty list", () => {
  seed({ id: "a" });
  expect(readRecentDocuments()).toEqual([]);
  seed("text");
  expect(readRecentDocuments()).toEqual([]);
  window.localStorage.setItem(RECENT_DOCUMENTS_KEY, "null");
  expect(readRecentDocuments()).toEqual([]);
});

test("malformed entries are dropped and the valid ones kept", () => {
  const valid: RecentDocument = { id: "ok", title: "Договор", stage: "protocol", openedAt: 5 };
  seed([
    valid,
    null,
    "строка",
    42,
    { id: "", title: null, stage: "analysis", openedAt: 1 },
    { id: 7, title: null, stage: "analysis", openedAt: 1 },
    { title: null, stage: "analysis", openedAt: 1 },
    { id: "bad-title", title: 5, stage: "analysis", openedAt: 1 },
    { id: "no-title-key", stage: "analysis", openedAt: 1 },
    { id: "bad-stage", title: null, stage: "export", openedAt: 1 },
    { id: "bad-time", title: null, stage: "analysis", openedAt: "1" },
    { id: "null-time", title: null, stage: "analysis", openedAt: null },
  ]);
  expect(readRecentDocuments()).toEqual([valid]);
});

test("a throwing getItem yields an empty list and remember does not throw", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("denied"); });
  expect(readRecentDocuments()).toEqual([]);
  expect(() => rememberDocument({ id: "a", title: "А", stage: "analysis" })).not.toThrow();
  expect(() => forgetDocument("a")).not.toThrow();
});

test("a throwing setItem is swallowed", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
  expect(() => rememberDocument({ id: "a", title: "А", stage: "analysis" })).not.toThrow();
  expect(() => forgetDocument("a")).not.toThrow();
  expect(readRecentDocuments()).toEqual([]);
});
