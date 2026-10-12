"""Compare the current protocol editions without changing their text."""
import re
from collections import Counter
from difflib import SequenceMatcher

from app.services.protocol_generator import ABSENT_EDITION, deletion_instruction

Segments = list[tuple[str, bool]]


class ExportHighlightError(ValueError):
    pass


def edition_segments(before: str, after: str, point_label: str | None = None) -> tuple[Segments, Segments]:
    if before == after:
        return [(before, False)], [(after, False)]
    # A new or excluded clause is a whole-text change; the service text in the
    # other column ("—", "Исключить пункт …") is not contract wording.
    if before.strip() in ("", ABSENT_EDITION):
        return [(before, False)], [(after, bool(after))]
    if after.strip() == "" or (point_label is not None and after.strip() == deletion_instruction(point_label)):
        return [(before, True)], [(after, False)]
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
        old_text, new_text = "".join(a[old_start:old_end]), "".join(b[new_start:new_end])
        # Whitespace-only edits (a doubled space, a line break) are not redlined.
        changed = tag != "equal" and not (old_text + new_text).isspace()
        if old_text:
            old.append((old_text, changed))
        if new_text:
            new.append((new_text, changed))
    if suffix:
        old.append((suffix, False))
        new.append((suffix, False))
    return _tidy(old), _tidy(new)


def _tidy(segments: Segments) -> Segments:
    """Bridge spaces between changed words so a strike or marker is continuous."""
    merged = _merge(segments)
    bridged = [
        (text, changed or (text.isspace() and 0 < i < len(merged) - 1 and merged[i - 1][1] and merged[i + 1][1]))
        for i, (text, changed) in enumerate(merged)
    ]
    return _merge(bridged)


def _merge(segments: Segments) -> Segments:
    merged: Segments = []
    for text, changed in segments:
        if merged and merged[-1][1] == changed:
            merged[-1] = (merged[-1][0] + text, changed)
        else:
            merged.append((text, changed))
    return merged
