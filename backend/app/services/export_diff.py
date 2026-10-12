"""Compare the current protocol editions without changing their text."""
import re
from collections import Counter
from difflib import SequenceMatcher


class ExportHighlightError(ValueError):
    pass


def edition_segments(before: str, after: str) -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    if before == after:
        return [(before, False)], [(after, False)]
    # Keep whitespace, punctuation, Cyrillic and paragraph breaks verbatim.
    a, b = (re.findall(r"\w+|\s+|[^\w\s]", text) for text in (before, after))
    start = 0
    while start < min(len(a), len(b)) and a[start] == b[start]:
        start += 1
    end_a, end_b = len(a), len(b)
    while end_a > start and end_b > start and a[end_a - 1] == b[end_b - 1]:
        end_a -= 1
        end_b -= 1
    prefix, suffix = "".join(a[:start]), "".join(a[end_a:])
    a, b = a[start:end_a], b[start:end_b]
    counts_a, counts_b = Counter(a), Counter(b)
    # Never silently approximate a legal redline or let pathological repeated
    # text block the local engine. Disabling highlighting still allows export.
    if len(before) + len(after) > 200_000 or sum(count * counts_b[token] for token, count in counts_a.items()) > 5_000_000:
        raise ExportHighlightError(
            "Одна из строк слишком велика для точного выделения правок. "
            "Разделите её на несколько строк или выключите выделение изменений в DOCX."
        )
    old, new = [(prefix, False)] if prefix else [], [(prefix, False)] if prefix else []
    for tag, old_start, old_end, new_start, new_end in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if old_start != old_end:
            old.append(("".join(a[old_start:old_end]), tag != "equal"))
        if new_start != new_end:
            new.append(("".join(b[new_start:new_end]), tag != "equal"))
    if suffix:
        old.append((suffix, False))
        new.append((suffix, False))
    return old, new
