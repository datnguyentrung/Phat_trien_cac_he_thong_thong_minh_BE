from __future__ import annotations

import unicodedata
from collections.abc import Callable

_HEADINGS = (
    (("tom tat", "nhu cau"), "### Tóm tắt nhu cầu của bạn"),
    (("canh bao",), "### Cảnh báo cần ưu tiên"),
    (("san pham", "tham khao"), "### Các sản phẩm được tìm thấy để tham khảo"),
    (("bang", "doi chieu"), "### Bảng đối chiếu nhanh"),
    (("bang", "so sanh"), "### Bảng đối chiếu nhanh"),
    (("ket luan",), "### Kết luận an toàn"),
    (("nguon", "gioi han"), "### Nguồn và giới hạn dữ liệu"),
)


def _plain_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(
        "d" if char == "đ" else char
        for char in decomposed
        if not unicodedata.combining(char)
    )


def _normalize_heading(line: str) -> str:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return line

    title = _plain_text(stripped.lstrip("#").strip())
    for keywords, canonical in _HEADINGS:
        if all(keyword in title for keyword in keywords):
            suffix = "\n" if line.endswith("\n") else ""
            return canonical + suffix
    return line


class FinalSummaryMarkdownStream:
    """Normalize contract headings while retaining incremental Markdown output."""

    def __init__(
        self,
        on_heading: Callable[[str], None] | None = None,
        flush_threshold: int = 250,
    ) -> None:
        self._pending = ""
        self._on_heading = on_heading
        self._seen_headings: set[str] = set()
        self._flush_threshold = flush_threshold

    def feed(self, text: str) -> list[str]:
        self._pending += text
        lines = self._pending.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            pending = lines.pop()
            if (
                len(pending) > self._flush_threshold
                and not pending.lstrip().startswith("#")
            ):
                # Flush long non-heading fragments immediately so clients see
                # long paragraphs progressively instead of one block. Heading
                # fragments stay buffered so canonicalization never breaks.
                self._pending = ""
                lines.append(pending)
            else:
                self._pending = pending
        else:
            self._pending = ""
        output: list[str] = []
        for line in lines:
            normalized = _normalize_heading(line)
            if self._on_heading is not None and normalized.startswith("### "):
                canonical = normalized.rstrip("\r\n")
                if canonical not in self._seen_headings:
                    self._seen_headings.add(canonical)
                    self._on_heading(canonical)
            output.append(normalized)
        return output

    def finish(self) -> str:
        remaining = _normalize_heading(self._pending)
        self._pending = ""
        return remaining
