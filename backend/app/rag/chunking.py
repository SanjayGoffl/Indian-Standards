from __future__ import annotations

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
LAYOUT_COLUMN_BREAK = "--- Layout Column Break ---"

# Structured table markers emitted by the document extractor. These markers
# are intentionally generic and domain-agnostic.
TABLE_START_MARKER = "[TABLE START]"
TABLE_END_MARKER = "[TABLE END]"

# Generic document-structure headings. These are intentionally domain-agnostic.

_MAJOR_HEADING_PATTERNS = (
    re.compile(
        r"^\s*(?:#+\s*)?"
        r"(?:milestone|chapter|section|phase|module|part|unit|appendix)"
        r"\b.*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:#+\s*)?"
        r"(?:table\s+of\s+contents|introduction|conclusion|"
        r"references|bibliography|abstract|summary)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:#+\s*)?\d+(?:\.\d+)*[.)]?\s+"
        r"[A-Z][^\n]{2,120}$",
        re.IGNORECASE,
    ),
)

# Common "label:" headings such as:
# "Objectives:", "Agents to be Implemented:", "Features:", etc.
_LABEL_HEADING_PATTERN = re.compile(
    r"^\s*(?:#+\s*)?[A-Za-z][A-Za-z0-9 &/()_-]{2,100}:\s*$"
)


def _split_normal_text(text: str) -> list[str]:
    """Split ordinary document text using the project's existing strategy."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def _find_table_blocks(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans for extractor-emitted table blocks."""
    spans: list[tuple[int, int]] = []
    cursor = 0

    while True:
        start = text.find(TABLE_START_MARKER, cursor)
        if start == -1:
            break

        end_marker_start = text.find(TABLE_END_MARKER, start + len(TABLE_START_MARKER))
        if end_marker_start == -1:
            break

        end = end_marker_start + len(TABLE_END_MARKER)
        spans.append((start, end))
        cursor = end

    return spans


def _split_table_block(table_block: str) -> list[str]:
    """Keep a structured table intact, splitting only between rows if needed."""
    if len(table_block) <= DEFAULT_CHUNK_SIZE:
        return [table_block.strip()] if table_block.strip() else []

    lines = [line.rstrip() for line in table_block.splitlines()]
    if not lines:
        return []

    try:
        start_idx = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == TABLE_START_MARKER
        )
        end_idx = next(
            index
            for index in range(len(lines) - 1, -1, -1)
            if lines[index].strip() == TABLE_END_MARKER
        )
    except StopIteration:
        # Defensive fallback for malformed markers. Preserve the prior
        # behavior rather than risking data loss.
        return _split_normal_text(table_block)

    row_pattern = re.compile(r"^\s*Table\s+\d+\s+row\s+\d+:")
    first_row_idx = next(
        (index for index in range(start_idx + 1, end_idx) if row_pattern.match(lines[index])),
        None,
    )

    # If the extractor format is not row-oriented, preserve the block instead
    # of making unsafe assumptions about its internal structure.
    if first_row_idx is None:
        return _split_normal_text(table_block)

    header_lines = lines[start_idx:first_row_idx]
    row_lines = lines[first_row_idx:end_idx]

    chunks: list[str] = []
    current_rows: list[str] = []

    def build_chunk(rows: list[str]) -> str:
        content = header_lines + rows + [lines[end_idx]]
        return "\n".join(content).strip()

    for row in row_lines:
        candidate_rows = current_rows + [row]
        candidate = build_chunk(candidate_rows)

        if current_rows and len(candidate) > DEFAULT_CHUNK_SIZE:
            chunks.append(build_chunk(current_rows))
            current_rows = [row]
        else:
            current_rows = candidate_rows

    if current_rows:
        chunks.append(build_chunk(current_rows))

    return chunks


# CSV markers emitted by app.rag.extractor.extract_csv().
CSV_ROW_MARKER_PATTERN = re.compile(
    r"^\s*---\s*Row\s+(\d+)\s*---\s*$",
    re.IGNORECASE,
)
CSV_COLUMNS_MARKER = "--- CSV Columns ---"


def _split_csv_rows(text: str) -> list[dict[str, str]]:
    """
    Convert extractor-generated CSV text into atomic row records.

    CSV is record-oriented data. Splitting it with a character-count
    text splitter can place the tail of one row beside the beginning of
    another row, allowing downstream generation to mix field values.

    Each CSV row is therefore kept as one retrieval unit. The row number,
    column header line, and optional filename prefix are retained so the
    record remains self-describing and searchable. This is deliberately
    schema-agnostic: no column names are hard-coded here.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    row_positions: list[tuple[int, int]] = []

    for index, line in enumerate(lines):
        match = CSV_ROW_MARKER_PATTERN.match(line)
        if match:
            row_positions.append((index, int(match.group(1))))

    if not row_positions:
        return []

    # Preserve only the self-describing prefix that is useful to every row.
    # In the current extractor this is the filename and CSV column header.
    prefix_lines: list[str] = []
    for line in lines[:row_positions[0][0]]:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower() == CSV_COLUMNS_MARKER.lower():
            prefix_lines.append(stripped)
            continue

        # The extractor may add a searchable file-name line before the CSV.
        if stripped.lower().startswith("file name:"):
            prefix_lines.append(stripped)

        # Keep the actual column header immediately following the marker.
        elif prefix_lines and prefix_lines[-1].lower() == CSV_COLUMNS_MARKER.lower():
            prefix_lines.append(stripped)

    records: list[dict[str, str]] = []

    for position, (start_index, row_number) in enumerate(row_positions):
        end_index = (
            row_positions[position + 1][0]
            if position + 1 < len(row_positions)
            else len(lines)
        )

        row_lines = [
            line.strip()
            for line in lines[start_index:end_index]
            if line.strip()
        ]

        if not row_lines:
            continue

        # Guard against malformed text containing another structural marker
        # inside a row. The row marker itself stays as the record boundary.
        content_lines = prefix_lines + row_lines
        content = "\n".join(content_lines).strip()

        if not content:
            continue

        records.append(
            {
                "content": content,
                "record_type": "csv_row",
                "csv_row_number": str(row_number),
            }
        )

    return records


def _split_text_preserving_tables(text: str) -> list[str]:
    """Split text while preventing extractor-emitted tables from being split arbitrarily."""
    spans = _find_table_blocks(text)
    if not spans:
        return _split_normal_text(text)

    chunks: list[str] = []
    cursor = 0

    for start, end in spans:
        before = text[cursor:start].strip()
        if before:
            chunks.extend(_split_normal_text(before))

        table_block = text[start:end].strip()
        if table_block:
            chunks.extend(_split_table_block(table_block))

        cursor = end

    after = text[cursor:].strip()
    if after:
        chunks.extend(_split_normal_text(after))

    return chunks


def _is_major_heading(line: str) -> bool:
    """
    Return True when a line is likely to introduce a logical document section.

    This is deliberately conservative. Numbered task lines such as
    "1. Build Retrieval Agent..." are NOT treated as headings unless they
    match a major-heading pattern or a clear heading label.
    """
    stripped = line.strip()

    if not stripped:
        return False

    # Markdown-style headings are always strong structural signals.
    if re.match(r"^#{1,6}\s+\S+", stripped):
        return True

    for pattern in _MAJOR_HEADING_PATTERNS:
        if pattern.match(stripped):
            return True

    if _LABEL_HEADING_PATTERN.match(stripped):
        # A long sentence ending in ':' is usually an introduction to a list,
        # not a structural heading (for example, "The most critical ...:").
        return len(stripped.rstrip(":").split()) <= 5

    return False


def _looks_like_task_or_bullet(line: str) -> bool:
    """
    Identify common list/task lines so they are not mistaken for section
    headings.
    """
    stripped = line.strip()

    if not stripped:
        return False

    if re.match(r"^[•●▪◦\-–—]\s+\S+", stripped):
        return True

    if re.match(r"^\d+[.)]\s+\S+", stripped):
        return True

    if re.match(r"^[a-zA-Z][.)]\s+\S+", stripped):
        return True

    return False


def _split_logical_sections(text: str) -> list[str]:
    """
    Preserve logical document sections when clear headings are present.

    A section begins at a recognized major heading and continues until the
    next recognized major heading. Text before the first recognized heading
    remains part of a leading section.

    This is useful for PDFs/DOCX/TXT that contain structured sections such as
    "Milestone 1", "Milestone 2", "Chapter 3", "Section 4", etc., while still
    falling back safely for ordinary prose.
    """
    lines = text.splitlines()

    if len(lines) < 2:
        return [text.strip()] if text.strip() else []

    sections: list[list[str]] = []
    current: list[str] = []
    found_heading = False

    for line in lines:
        stripped = line.strip()

        # Preserve blank lines inside the current section.
        if not stripped:
            if current:
                current.append("")
            continue

        is_heading = _is_major_heading(stripped)

        # Avoid interpreting numbered/bulleted tasks as major headings.
        if is_heading and _looks_like_task_or_bullet(stripped):
            is_heading = False

        if is_heading:
            found_heading = True

            if current:
                section_text = "\n".join(current).strip()
                if section_text:
                    sections.append(current)
                current = []

            current.append(stripped)
            continue

        current.append(line)

    if current:
        section_text = "\n".join(current).strip()
        if section_text:
            sections.append(current)

    if not found_heading:
        return [text.strip()] if text.strip() else []

    return [
        "\n".join(section).strip()
        for section in sections
        if "\n".join(section).strip()
    ]


def _chunk_logical_sections(
    text: str,
) -> list[str]:
    """
    Preserve detected logical sections as complete chunks whenever possible.

    If a logical section is larger than DEFAULT_CHUNK_SIZE, it is split using
    the existing recursive splitter. This keeps long sections scalable without
    changing the established fallback behavior.
    """
    logical_sections = _split_logical_sections(text)

    if not logical_sections:
        return []

    chunks: list[str] = []

    for section in logical_sections:
        if len(section) <= DEFAULT_CHUNK_SIZE:
            chunks.append(section)
        else:
            chunks.extend(_split_text_preserving_tables(section))

    return chunks


def _split_layout_aware_text(text: str) -> list[str]:
    """
    Split OCR text while respecting explicit layout-column boundaries.

    Each visual column is processed independently. Within each column, logical
    document sections are preserved before falling back to recursive splitting.
    """
    sections = [
        section.strip()
        for section in text.split(LAYOUT_COLUMN_BREAK)
        if section.strip()
    ]

    if len(sections) <= 1:
        return _chunk_logical_sections(text)

    chunks: list[str] = []

    for section in sections:
        chunks.extend(_chunk_logical_sections(section))

    return chunks


def chunk_text(text: str) -> list[str]:
    """
    Split extracted document text into retrieval-friendly chunks.

    Behavior:
      1. Empty input -> no chunks.
      2. Image/layout-aware OCR -> respect visual-column boundaries and then
         preserve logical document sections.
      3. Structured text with clear headings -> preserve each logical section
         as a chunk when it fits within the normal chunk size.
      4. Long sections -> use the existing RecursiveCharacterTextSplitter.
      5. Ordinary unstructured text -> retain the original splitter behavior.

    The important optimization is that a section such as:

        Milestone 3 (Week 5-6)
        1. ...
        2. ...
        3. ...
        4. ...

    stays together instead of being split arbitrarily between unrelated
    milestone chunks, while no domain-specific term is hard-coded.
    """
    if not text or not text.strip():
        return []

    if LAYOUT_COLUMN_BREAK in text:
        return _split_layout_aware_text(text)

    logical_sections = _split_logical_sections(text)

    # If no meaningful document structure was detected, retain the original
    # behavior for ordinary text while still protecting structured tables.
    if len(logical_sections) <= 1:
        return _split_text_preserving_tables(text)

    return _chunk_logical_sections(text)


# =====================================================================
# Section-aware chunk records
# =====================================================================

def _section_heading_from_text(section: str) -> str | None:
    """Return the leading structural heading when the section has one."""
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if _is_major_heading(stripped) and not _looks_like_task_or_bullet(stripped):
            heading = re.sub(r"^#{1,6}\s*", "", stripped).strip()
            return heading or None

        break

    return None


def _chunk_section_records(section: str) -> list[dict[str, str]]:
    """Chunk one logical section and preserve its heading on every chunk."""
    section = section.strip()
    if not section:
        return []

    heading = _section_heading_from_text(section)

    if len(section) <= DEFAULT_CHUNK_SIZE:
        parts = [section]
    else:
        parts = _split_text_preserving_tables(section)

    records: list[dict[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        record = {"content": part}
        if heading:
            record["section_heading"] = heading
        records.append(record)

    return records


def chunk_text_with_sections(
    text: str,
    file_type: str | None = None,
) -> list[dict[str, str]]:
    """
    Return retrieval chunks with optional structural metadata.

    CSV is handled separately because a CSV row is an atomic record rather
    than ordinary prose. Other file types retain the established chunking
    behavior, so this change does not alter the project's PDF/DOCX/TXT/image
    chunking strategy.

    Args:
        text: Extracted document text.
        file_type: Optional extension such as ``"csv"`` or ``".csv"``.
    """
    if not text or not text.strip():
        return []

    normalized_file_type = (file_type or "").strip().lower()
    if normalized_file_type.startswith("."):
        normalized_file_type = normalized_file_type[1:]

    # Critical CSV fix: one complete row = one retrieval chunk.
    if normalized_file_type == "csv":
        csv_records = _split_csv_rows(text)
        if csv_records:
            return csv_records

    # Defensive fallback: if the caller forgot to pass file_type but the
    # extractor markers are present, still preserve CSV row boundaries.
    if "--- CSV Columns ---" in text and CSV_ROW_MARKER_PATTERN.search(text):
        csv_records = _split_csv_rows(text)
        if csv_records:
            return csv_records

    if LAYOUT_COLUMN_BREAK in text:
        column_sections = [
            section.strip()
            for section in text.split(LAYOUT_COLUMN_BREAK)
            if section.strip()
        ]

        if len(column_sections) <= 1:
            return chunk_text_with_sections(
                column_sections[0] if column_sections else text
            )

        records: list[dict[str, str]] = []
        for column in column_sections:
            logical_sections = _split_logical_sections(column)
            if len(logical_sections) <= 1:
                records.extend(
                    {
                        "content": chunk,
                    }
                    for chunk in _split_text_preserving_tables(column)
                    if chunk.strip()
                )
            else:
                for section in logical_sections:
                    records.extend(_chunk_section_records(section))
        return records

    logical_sections = _split_logical_sections(text)

    # Keep the established fallback for ordinary unstructured text.
    if len(logical_sections) <= 1:
        return [
            {"content": chunk}
            for chunk in _split_text_preserving_tables(text)
            if chunk.strip()
        ]

    records: list[dict[str, str]] = []
    for section in logical_sections:
        records.extend(_chunk_section_records(section))

    return records


if __name__ == "__main__":
    sample = """Project Milestones

Milestone 1 (Week 1-2)
1. Study RAG architecture.
2. Design system architecture.
3. Develop ingestion.
4. Validate retrieval.

Milestone 2 (Week 3-4)
1. Build Query Understanding Agent.
2. Build Retrieval Agent.
3. Build Response Generation Agent.
4. Implement orchestration.

Milestone 3 (Week 5-6)
1. Build Clarification Agent.
2. Build Conversation Memory Agent.
3. Integrate Voice Input and Text-to-Speech.
4. Build Response Transparency Panel.

Milestone 4 (Week 7-8)
1. Develop Analytics.
2. Conduct end-to-end testing.
3. Optimize retrieval quality.
4. Prepare documentation.
"""

    chunks = chunk_text(sample)

    print("Chunking check")
    print(f"Generated chunks: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n--- CHUNK {index} ---")
        print(chunk)
