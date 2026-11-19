"""Source-checked XML metadata decoding for the direct WebSocket transport.

Only event text is normalized; offsets/durations are copied verbatim. Unknown
mismatches are left intact so the existing strict subtitle validation reports
them. This module has no network or subtitle pipeline dependencies.
"""
import html
import re


_ENTITY = re.compile(r"&(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);")


def _decode_xml(text):
    # Decode exactly one layer, only complete XML entities. html.unescape alone
    # also rewrites incomplete HTML names such as '&not', which may be literal.
    return _ENTITY.sub(lambda match: html.unescape(match[0]), text)


def normalize_boundary_text(source, boundaries):
    """Return copied events whose escaped text can be verified in the source.

    Preserve literal entity-looking source text and remain idempotent. There is
    one narrowly verified service anomaly: immediately after a standalone '&',
    the next ASCII word may be a same-length slice of escaped source using the
    original source indices (e.g. System -> 'mp; Sy'). Repair only if that exact
    slice reproduces the event AND the following event anchors the word's end.
    Never use a fuzzy match or invent timing for a missing event.
    """
    result = []
    cursor = 0
    escaped = None
    previous = ""
    for index, event in enumerate(boundaries):
        event = dict(event)
        raw = event["text"]
        decoded = _decode_xml(raw)
        raw_start = source.find(raw, cursor) if raw.strip() else -1
        decoded_start = source.find(decoded, cursor) if decoded.strip() else -1
        chosen, start = raw, raw_start
        # Prefer literal source on a tie, preventing '&amp;' from being decoded
        # again when that is what the author actually wrote.
        if decoded_start >= 0 and (raw_start < 0 or decoded_start < raw_start):
            chosen, start = decoded, decoded_start
        if start < 0 and previous == "&" and cursor and source[cursor - 1] == "&":
            word = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)", source[cursor:])
            if word and index + 1 < len(boundaries):
                word_start = cursor + word.start(1)
                word_end = cursor + word.end(1)
                following = _decode_xml(boundaries[index + 1]["text"])
                next_start = source.find(following, word_end) if following.strip() else -1
                if escaped is None:
                    escaped = html.escape(source, quote=True)
                if (len(raw) == word_end - word_start
                        and escaped[word_start:word_end] == raw
                        and raw != source[word_start:word_end]
                        and next_start >= word_end
                        and not re.search(r"\w", source[word_end:next_start])):
                    chosen, start = source[word_start:word_end], word_start
        if chosen != raw:
            event.setdefault("raw_text", raw)
            event["text"] = chosen
        if start >= 0:
            cursor = start + len(chosen)
        previous = chosen
        result.append(event)
    return result
