"""Text chunking for the RAG pipeline.

Chunks are built to respect concept boundaries rather than naive character
windows: we split on natural paragraphs first and only break a paragraph apart
(marking it as a forced split) when it exceeds the size budget.

Token counts are approximated as 1 token ~= 4 characters. This is a documented
assumption to avoid a heavy tokenizer dependency at this stage; swap
`count_tokens` for a real tokenizer (e.g. tiktoken) if exact counts are needed.
"""
import re
from dataclasses import dataclass

CHARS_PER_TOKEN = 4
MAX_TOKENS = 500
MIN_TOKENS = 100
OVERLAP_TOKENS = 50

MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN      # ~2000
MIN_CHARS = MIN_TOKENS * CHARS_PER_TOKEN      # ~400
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN  # ~200

_PARAGRAPH_RE = re.compile(r"\n\s*\n+")
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")


@dataclass
class TextChunk:
    text: str
    forced_split: bool


def count_tokens(text: str) -> int:
    """Approximate token count (1 token ~= 4 characters, rounded up)."""
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


@dataclass
class _Segment:
    text: str
    forced: bool


def _split_oversized_paragraph(paragraph: str) -> list[str]:
    """Break a paragraph larger than MAX_CHARS on single newlines, then on
    sentence boundaries, then on hard character windows as a last resort."""
    pieces: list[str] = []
    for line in (paragraph.split("\n") if "\n" in paragraph else [paragraph]):
        line = line.strip()
        if not line:
            continue
        if len(line) <= MAX_CHARS:
            pieces.append(line)
            continue
        # Still too big: accumulate whole sentences up to MAX_CHARS.
        buffer = ""
        for sentence in _SENTENCE_RE.split(line):
            if len(sentence) > MAX_CHARS:
                if buffer:
                    pieces.append(buffer)
                    buffer = ""
                for start in range(0, len(sentence), MAX_CHARS):
                    pieces.append(sentence[start:start + MAX_CHARS])
            elif not buffer:
                buffer = sentence
            elif len(buffer) + 1 + len(sentence) <= MAX_CHARS:
                buffer = f"{buffer} {sentence}"
            else:
                pieces.append(buffer)
                buffer = sentence
        if buffer:
            pieces.append(buffer)
    return pieces


def _segments(text: str) -> list[_Segment]:
    segments: list[_Segment] = []
    for paragraph in _PARAGRAPH_RE.split(text.strip()):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= MAX_CHARS:
            segments.append(_Segment(paragraph, forced=False))
        else:
            for piece in _split_oversized_paragraph(paragraph):
                segments.append(_Segment(piece, forced=True))
    return segments


def _overlap_prefix(previous_text: str) -> str:
    """Last OVERLAP_CHARS of the previous chunk, trimmed to a word boundary."""
    tail = previous_text[-OVERLAP_CHARS:]
    space = tail.find(" ")
    if space != -1:
        tail = tail[space + 1:]
    return tail.strip()


def chunk_text(text: str) -> list[TextChunk]:
    """Split source text into overlapping, concept-preserving chunks."""
    segments = _segments(text)
    if not segments:
        return []

    # Greedily pack whole segments into chunks up to MAX_CHARS.
    packed: list[_Segment] = []
    current = ""
    current_forced = False
    for seg in segments:
        if not current:
            current, current_forced = seg.text, seg.forced
        elif len(current) + 2 + len(seg.text) <= MAX_CHARS:
            current = f"{current}\n\n{seg.text}"
            current_forced = current_forced or seg.forced
        else:
            packed.append(_Segment(current, current_forced))
            current, current_forced = seg.text, seg.forced
    if current:
        packed.append(_Segment(current, current_forced))

    # Merge a too-small trailing chunk into its predecessor when it fits.
    if len(packed) >= 2 and len(packed[-1].text) < MIN_CHARS:
        prev, last = packed[-2], packed[-1]
        if len(prev.text) + 2 + len(last.text) <= MAX_CHARS:
            packed[-2] = _Segment(
                f"{prev.text}\n\n{last.text}", prev.forced or last.forced
            )
            packed.pop()

    # Apply overlap: prefix each chunk (except the first) with the tail of the
    # previous chunk's base text.
    chunks: list[TextChunk] = []
    for i, seg in enumerate(packed):
        if i == 0:
            chunks.append(TextChunk(seg.text, seg.forced))
        else:
            prefix = _overlap_prefix(packed[i - 1].text)
            joined = f"{prefix} {seg.text}".strip() if prefix else seg.text
            chunks.append(TextChunk(joined, seg.forced))
    return chunks
