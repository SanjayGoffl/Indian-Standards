import logging
import os
import re
import tkinter as tk
from tkinter import filedialog

import pymupdf
from docx import Document
import pandas as pd

logger = logging.getLogger(__name__)

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

OUTPUT_FOLDER = os.path.join(
    BASE_FOLDER,
    "extracted_text"
)

# File selector
def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select Document",
        filetypes=[
            ("Supported Files", "*.pdf *.docx *.txt *.csv *.jpg *.jpeg *.png"),
            ("PDF Files", "*.pdf"),
            ("DOCX Files", "*.docx"),
            ("TXT Files", "*.txt"),
            ("CSV Files", "*.csv"),
            ("Image Files", "*.jpg *.jpeg *.png")
        ]
    )

    root.destroy()

    return file_path

# -------------------------------------------------------------------
# Generic table extraction helpers
# -------------------------------------------------------------------

def _normalize_table_cell(value):
    """Normalize a table cell without changing its meaning."""
    if value is None:
        return ""

    text = re.sub(r"\s+", " ", str(value)).strip()
    return text


def _table_block_text(table, table_index):
    """
    Serialize a native document table into a self-contained, row-aware block.

    Every row repeats the column/header relationship so retrieval remains
    meaningful even when a large table is later split into separate chunks.
    This representation is intentionally domain-agnostic.
    """
    try:
        rows = table.extract()
    except Exception as error:
        logger.warning(
            "[TABLE] Could not extract table %d: %s",
            table_index,
            error,
        )
        return ""

    if not rows:
        return ""

    normalized_rows = []
    max_columns = 0

    for row in rows:
        if not row:
            continue

        values = [
            _normalize_table_cell(cell)
            for cell in row
        ]
        normalized_rows.append(values)
        max_columns = max(max_columns, len(values))

    if not normalized_rows or max_columns == 0:
        return ""

    headers = list(normalized_rows[0])
    headers.extend(
        [
            f"Column {index + 1}"
            for index in range(len(headers), max_columns)
        ]
    )

    # Generic fallback when the first row does not contain usable headers.
    for index, header in enumerate(headers):
        if not header:
            headers[index] = f"Column {index + 1}"

    lines = [
        "[TABLE START]",
        f"Table {table_index + 1} columns: "
        + " | ".join(headers),
    ]

    data_rows = normalized_rows[1:]

    # If a table has no clear header row, preserve the first row as data too.
    if not data_rows:
        data_rows = normalized_rows

    for row_index, row in enumerate(data_rows, start=1):
        padded = list(row) + [""] * (max_columns - len(row))
        pairs = [
            f"{headers[column_index]} = {padded[column_index]}"
            for column_index in range(max_columns)
            if padded[column_index]
        ]

        if pairs:
            lines.append(
                f"Table {table_index + 1} row {row_index}: "
                + " | ".join(pairs)
            )

    lines.append("[TABLE END]")
    return "\n".join(lines)


def _table_bboxes(page):
    """Return native PyMuPDF table objects and their bounding boxes."""
    try:
        finder = page.find_tables()
        tables = list(finder.tables or [])
    except Exception as error:
        logger.debug(
            "[TABLE] Native table detection unavailable on page: %s",
            error,
        )
        return []

    result = []
    for table_index, table in enumerate(tables):
        bbox = getattr(table, "bbox", None)
        if not bbox or len(bbox) < 4:
            continue

        try:
            result.append(
                {
                    "index": table_index,
                    "table": table,
                    "bbox": tuple(float(value) for value in bbox[:4]),
                }
            )
        except (TypeError, ValueError):
            continue

    return result



def _extract_pdf_tables(page):
    """Return structured table text detected by PyMuPDF on a native-text page."""
    table_infos = _table_bboxes(page)
    if not table_infos:
        return []

    table_blocks = []

    for table_info in table_infos:
        table_text = _table_block_text(
            table_info["table"],
            table_info["index"],
        )
        if table_text:
            table_blocks.append(table_text)

    return table_blocks


def _extract_docx_tables(document):
    """
    Extract DOCX tables into the same generic row-aware representation used
    for PDFs. Native paragraphs remain unchanged.
    """
    table_blocks = []

    for table_index, table in enumerate(document.tables):
        try:
            rows = []
            for row in table.rows:
                rows.append([
                    _normalize_table_cell(cell.text)
                    for cell in row.cells
                ])

            if not rows:
                continue

            normalized_rows = [
                row
                for row in rows
                if any(row)
            ]

            if not normalized_rows:
                continue

            max_columns = max(
                len(row)
                for row in normalized_rows
            )

            headers = list(normalized_rows[0])
            headers.extend(
                [
                    f"Column {index + 1}"
                    for index in range(len(headers), max_columns)
                ]
            )

            for index, header in enumerate(headers):
                if not header:
                    headers[index] = f"Column {index + 1}"

            lines = [
                "[TABLE START]",
                f"Table {table_index + 1} columns: "
                + " | ".join(headers),
            ]

            for row_index, row in enumerate(normalized_rows[1:], start=1):
                padded = list(row) + [""] * (max_columns - len(row))
                pairs = [
                    f"{headers[column_index]} = {padded[column_index]}"
                    for column_index in range(max_columns)
                    if padded[column_index]
                ]
                if pairs:
                    lines.append(
                        f"Table {table_index + 1} row {row_index}: "
                        + " | ".join(pairs)
                    )

            lines.append("[TABLE END]")
            table_blocks.append("\n".join(lines))

        except Exception as error:
            logger.warning(
                "[DOCX] Failed to extract table %d: %s",
                table_index,
                error,
            )

    return table_blocks


# PDF extraction
def extract_pdf(file_path, page_progress_callback=None):
    """
    Hybrid PDF extraction.

    Strategy:
      1. Extract native text from each PDF page using PyMuPDF.
      2. If a page has sufficient native text, use it directly.
      3. If a page is empty or contains very little text, render that
         page and run PaddleOCR on it.
      4. This allows normal PDFs to bypass OCR while scanned/
         handwritten pages still use OCR.
    """

    from app.services.ocr_service import ocr_service

    pdf = pymupdf.open(file_path)
    total_pages = len(pdf)

    text_parts = []
    page_metadata = []

    # Minimum amount of native text that we consider sufficient.
    # Pages below this threshold are considered likely scanned/image
    # pages and are sent through OCR.
    MIN_NATIVE_TEXT_CHARS = 40

    logger.info(
        "[PDF] Hybrid extraction started for '%s' (%d pages)",
        os.path.basename(file_path),
        total_pages
    )

    try:
        for page_index in range(total_pages):
            page_number = page_index + 1
            page = pdf[page_index]

            # First attempt: native PDF text extraction.
            native_text = page.get_text("text") or ""
            native_text = native_text.strip()

            # Detect native tables before storing page text so table values can
            # also be provided as explicit row/column relationships. Keep the
            # original native text unchanged to avoid altering existing PDF
            # reading order or list/bullet extraction behavior.
            table_blocks = []
            if native_text:
                table_blocks = _extract_pdf_tables(page)

            if len(native_text) >= MIN_NATIVE_TEXT_CHARS or table_blocks:
                logger.info(
                    "[PDF] Page %d/%d: native text found "
                    "(%d chars) - OCR skipped",
                    page_number,
                    total_pages,
                    len(native_text)
                )

                page_text_parts = []

                # Put structured table evidence before flattened page text.
                # The prompt explicitly instructs the LLM to prefer this
                # representation for table-value questions.
                if table_blocks:
                    page_text_parts.append(
                        "[STRUCTURED TABLE EVIDENCE]\n"
                        + "\n\n".join(table_blocks)
                        + "\n[END STRUCTURED TABLE EVIDENCE]"
                    )
                    logger.info(
                        "[TABLE] Page %d/%d: detected %d native table(s)",
                        page_number,
                        total_pages,
                        len(table_blocks),
                    )

                if native_text:
                    page_text_parts.append(native_text)

                page_content = "\n\n".join(
                    part.strip()
                    for part in page_text_parts
                    if part and part.strip()
                )

                text_parts.append(
                    f"\n--- Page {page_number} ---\n"
                    f"{page_content}"
                )

                page_metadata.append(
                    {
                        "page_number": page_number,
                        "confidence": 1.0,
                        "source_type": "pdf_text",
                        "extraction_method": "pymupdf"
                    }
                )
            else:
                # Fallback: OCR only this page
                logger.info(
                    "[OCR] Page %d/%d has insufficient native text "
                    "(%d chars) - running PaddleOCR",
                    page_number,
                    total_pages,
                    len(native_text)
                )

                # Render page as image.
                pixmap = page.get_pixmap(
                    dpi=150,
                    alpha=False
                )

                image_bytes = pixmap.tobytes("png")

                try:
                    ocr_result = ocr_service.run_ocr_on_image(
                        image_bytes
                    )

                    ocr_text = (
                        ocr_result.get("text", "")
                        if isinstance(ocr_result, dict)
                        else ""
                    )

                    ocr_text = ocr_text.strip()

                    confidence = (
                        ocr_result.get("confidence", 0.0)
                        if isinstance(ocr_result, dict)
                        else 0.0
                    )

                    if ocr_text:
                        logger.info(
                            "[OCR] Page %d/%d extracted %d chars "
                            "(confidence %.2f)",
                            page_number,
                            total_pages,
                            len(ocr_text),
                            confidence
                        )

                        text_parts.append(
                            f"\n--- Page {page_number} (OCR) ---\n"
                            f"{ocr_text}"
                        )

                        page_metadata.append(
                            {
                                "page_number": page_number,
                                "confidence": confidence,
                                "source_type": "pdf_ocr_page",
                                "extraction_method": "ppocr"
                            }
                        )
                    elif native_text:
                        # If OCR returned nothing but native PDF
                        # text existed, keep the native text.
                        text_parts.append(
                            f"\n--- Page {page_number} ---\n"
                            f"{native_text}"
                        )

                        page_metadata.append(
                            {
                                "page_number": page_number,
                                "confidence": 1.0,
                                "source_type": "pdf_text",
                                "extraction_method": "pymupdf"
                            }
                        )
                    else:
                        logger.warning(
                            "[PDF] Page %d/%d contains no readable "
                            "native text or OCR text",
                            page_number,
                            total_pages
                        )

                except Exception as ocr_error:
                    logger.exception(
                        "[OCR] Failed on PDF page %d: %s",
                        page_number,
                        ocr_error
                    )

                    # Don't lose native text if it existed.
                    if native_text:
                        text_parts.append(
                            f"\n--- Page {page_number} ---\n"
                            f"{native_text}"
                        )

                        page_metadata.append(
                            {
                                "page_number": page_number,
                                "confidence": 1.0,
                                "source_type": "pdf_text",
                                "extraction_method": "pymupdf"
                            }
                        )

            # Progress callback
            if page_progress_callback:
                try:
                    page_progress_callback(
                        page_number,
                        total_pages
                    )
                except Exception as callback_error:
                    logger.warning(
                        "[PDF] Progress callback failed: %s",
                        callback_error
                    )

    finally:
        pdf.close()

    combined_text = "\n".join(text_parts)

    # Create image/content records for OCR-derived pages.
    images_metadata = []

    for metadata in page_metadata:
        if metadata.get("source_type") == "pdf_ocr_page":
            page_number = metadata["page_number"]

            # Find OCR text belonging to this page.
            page_marker = (
                f"--- Page {page_number} (OCR) ---"
            )

            page_text = ""

            for block in text_parts:
                if block.startswith(page_marker):
                    page_text = block.replace(
                        page_marker,
                        "",
                        1
                    ).strip()
                    break

            if page_text:
                images_metadata.append(
                    {
                        "content": (
                            "[OCR Page Content "
                            f"(Confidence: "
                            f"{metadata.get('confidence', 0.0):.2f})]\n"
                            f"{page_text}"
                        ),
                        "metadata": {
                            "page_number": page_number,
                            "confidence": metadata.get(
                                "confidence",
                                0.0
                            ),
                            "source_type": "pdf_ocr_page",
                            "extraction_method": "ppocr"
                        }
                    }
                )

    return {
        "text": combined_text,
        "images": images_metadata
    }

# DOCX extraction
def extract_docx(file_path):
    from app.services.ocr_service import ocr_service
    from app.utils.image_filter import is_valid_document_image

    document = Document(file_path)
    text = ""
    images_metadata = []

    for paragraph in document.paragraphs:
        paragraph_text = paragraph.text.strip()

        if paragraph_text:
            text += paragraph_text + "\n"

    # Preserve DOCX tables as explicit row/column relationships. The existing
    # paragraph extraction remains unchanged; table blocks are appended only
    # when tables are actually present.
    docx_table_blocks = _extract_docx_tables(document)
    if docx_table_blocks:
        text += "\n" + "\n\n".join(docx_table_blocks) + "\n"

    image_count = 0
    MAX_IMAGES = 20
    page_hashes_map = {}

    # Extract images from docx parts
    for rel in document.part.rels.values():
        if "image" not in rel.target_ref:
            continue

        if image_count >= MAX_IMAGES:
            break

        try:
            image_data = rel.target_part.blob

            # Filter out tiny/repeated logo images
            valid, reason = is_valid_document_image(
                image_data,
                page_number=1,
                page_hashes_map=page_hashes_map
            )

            if not valid:
                logger.info(
                    "[DOCX] Skipping image %d: %s",
                    image_count,
                    reason
                )
                image_count += 1
                continue

            # Run PP-OCRv5 Mobile on embedded DOCX image
            ocr_result = ocr_service.run_ocr_on_image(
                image_data
            )

            ocr_text = (
                ocr_result.get("text", "")
                if isinstance(ocr_result, dict)
                else ""
            )

            ocr_text = ocr_text.strip()

            if ocr_text:
                images_metadata.append(
                    {
                        "content": (
                            f"[Image OCR Text: {ocr_text}]"
                        ),
                        "metadata": {
                            "image_index": image_count,
                            "source_type": "docx_image",
                            "extraction_method": "ppocr"
                        }
                    }
                )

            image_count += 1

        except Exception as error:
            print(
                f"Failed to process image in DOCX: {error}"
            )
            image_count += 1

    return {
        "text": text,
        "images": images_metadata
    }

# TXT extraction
def extract_txt(file_path):
    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1"
    ]

    for encoding in encodings:
        try:
            with open(
                file_path,
                "r",
                encoding=encoding
            ) as file:
                return file.read()

        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Unable to read the TXT file."
    )

# CSV extraction
def extract_csv(file_path):
    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1"
    ]

    dataframe = None
    last_error = None

    for encoding in encodings:
        try:
            dataframe = pd.read_csv(
                file_path,
                sep=None,
                engine="python",
                encoding=encoding,
                on_bad_lines="skip",
                comment="#"
            )
            break

        except Exception as error:
            last_error = error

    if dataframe is None:
        raise ValueError(
            f"Unable to read CSV file: {last_error}"
        )

    if dataframe.empty:
        return ""

    text = ""

    columns = list(dataframe.columns)

    text += "--- CSV Columns ---\n"
    text += ", ".join(
        str(column)
        for column in columns
    )
    text += "\n"

    for index, row in dataframe.iterrows():
        text += (
            f"\n--- Row {index + 1} ---\n"
        )

        for column in columns:
            value = row[column]

            if pd.isna(value):
                value = ""

            text += (
                f"{column}: "
                f"{str(value).strip()}\n"
            )

    return text

# Image extraction


def _as_float(value):
    """Safely coerce OCR geometry values to float."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bbox_from_block(block):
    """Return a normalized rectangular bbox from OCR geometry."""
    x1 = _as_float(block.get("x1"))
    y1 = _as_float(block.get("y1"))
    x2 = _as_float(block.get("x2"))
    y2 = _as_float(block.get("y2"))

    if None not in (x1, y1, x2, y2):
        return [
            [min(x1, x2), min(y1, y2)],
            [max(x1, x2), min(y1, y2)],
            [max(x1, x2), max(y1, y2)],
            [min(x1, x2), max(y1, y2)],
        ]

    raw_bbox = block.get("bbox")
    if raw_bbox is None:
        return None

    points = []
    try:
        for point in raw_bbox:
            if len(point) < 2:
                continue
            px = _as_float(point[0])
            py = _as_float(point[1])
            if px is not None and py is not None:
                points.append([px, py])
    except (TypeError, ValueError):
        return None

    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]

    return [
        [min(xs), min(ys)],
        [max(xs), min(ys)],
        [max(xs), max(ys)],
        [min(xs), max(ys)],
    ]


def _block_geometry(block):
    """Return stable scalar geometry for an OCR block."""
    bbox = _bbox_from_block(block)
    if not bbox:
        return None

    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]

    x1 = min(xs)
    y1 = min(ys)
    x2 = max(xs)
    y2 = max(ys)

    return {
        "bbox": bbox,
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "cx": (x1 + x2) / 2.0,
        "cy": (y1 + y2) / 2.0,
        "width": max(0.0, x2 - x1),
        "height": max(0.0, y2 - y1),
    }


def _median(values, default=0.0):
    values = [float(value) for value in values if value is not None]
    if not values:
        return float(default)
    values.sort()
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0


def _is_bullet_item(text):
    """Detect common OCR bullet/list prefixes generically."""
    stripped = str(text or "").strip()
    return stripped.startswith((
        "•", "·", "◦", "▪", "‣", "⁃", "-", "–", "—", "*"
    ))


def _strip_bullet(text):
    stripped = str(text or "").strip()
    return re.sub(r"^[•·◦▪‣⁃\-*–—\s]+", "", stripped).strip()


def _numbered_prefix(text):
    """Return a leading numeric list/heading marker, if present."""
    match = re.match(
        r"^\s*(\d{1,2})\s*[.)]\s+\S+",
        str(text or ""),
    )
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _is_numbered_heading(text):
    stripped = str(text or "").strip()
    if not stripped or _is_bullet_item(stripped):
        return False
    return _numbered_prefix(stripped) is not None


def _is_strong_textual_heading(text):
    """Detect compact title-like headings without document-specific words."""
    stripped = str(text or "").strip()
    if not stripped or _is_bullet_item(stripped):
        return False

    words = stripped.split()
    if not 1 <= len(words) <= 6:
        return False

    # Sentence-like lines are body content, not headings.  Question headings
    # are intentionally allowed because handwritten notes often use them.
    if stripped.endswith((".", ",", ";", ":")) and not stripped.endswith("?"):
        return False

    alpha = [char for char in stripped if char.isalpha()]
    if not alpha:
        return False

    title_case_words = sum(
        1
        for word in words
        if word and word[0].isupper()
    )
    title_ratio = title_case_words / max(1, len(words))

    upper_ratio = sum(char.isupper() for char in alpha) / len(alpha)

    # Strong signals for compact section labels:
    #   - very short title-like labels (for example "Benefits" or
    #     "Key Features")
    #   - clearly title-cased multi-word headings
    #   - all-caps labels
    #   - short question-like headings
    #
    # Do not treat a generic short sentence such as "Protect the
    # environment" as a heading merely because it is short. OCR often
    # drops bullet markers from handwritten lists, so word-count alone is
    # not a reliable heading signal.
    if stripped.endswith("?") and len(words) <= 8:
        return True

    if len(words) <= 2 and title_ratio >= 0.50:
        return True

    return (
        title_ratio >= 0.80
        or upper_ratio >= 0.55
    )


def _mark_numbered_list_sequences(column_blocks, median_height):
    """Mark repeated numbered blocks as list items rather than headings."""
    numbered = []

    for index, block in enumerate(column_blocks):
        number = _numbered_prefix(block.get("text"))
        if number is None:
            continue

        geometry = block.get("geometry") or {}
        numbered.append((index, number, geometry))

    if len(numbered) < 2:
        return

    for (left_index, left_number, left_geometry), (right_index, right_number, right_geometry) in zip(
        numbered,
        numbered[1:],
    ):
        if right_number != left_number + 1:
            continue

        if not left_geometry or not right_geometry:
            continue

        vertical_gap = float(right_geometry.get("y1") or 0.0) - float(
            left_geometry.get("y2") or 0.0
        )
        if vertical_gap < 0:
            vertical_gap = 0.0

        left_height = float(left_geometry.get("height") or 0.0)
        right_height = float(right_geometry.get("height") or 0.0)
        height_ratio = max(
            left_height,
            right_height,
            1.0,
        ) / max(
            min(left_height, right_height) if min(left_height, right_height) > 0 else 1.0,
            1.0,
        )

        # Consecutive numbered lines that sit reasonably close together and
        # share similar text geometry form a numbered procedure/list.
        if (
            vertical_gap <= max(median_height * 5.0, 120.0)
            and height_ratio <= 1.60
        ):
            column_blocks[left_index]["is_numbered_list_item"] = True
            column_blocks[right_index]["is_numbered_list_item"] = True


def _looks_like_heading(block, median_height):
    """
    Detect a section/title-like OCR block without knowing the document domain.

    Numbered blocks that are part of a consecutive list/procedure are explicitly
    excluded. Short title-like lines are also accepted even when handwriting
    does not produce a useful font-size difference.
    """
    text = str(block.get("text") or "").strip()
    if not text or _is_bullet_item(text):
        return False

    # A sequence such as 1) ..., 2) ..., 3) ... is list/procedure content, not
    # three independent section headings.
    if block.get("is_numbered_list_item"):
        return False

    if _is_numbered_heading(text):
        return True

    # Compact textual headings such as "Key Features", "Benefits", or
    # "How it works?" are commonly represented by OCR with the same font size
    # as body text. Recognize strong title-like wording generically.
    if _is_strong_textual_heading(text):
        return True

    geometry = block.get("geometry") or {}
    height = float(geometry.get("height") or 0.0)
    if median_height <= 0.0 or height < median_height * 1.20:
        return False

    if len(text) > 90 or len(text.split()) > 14:
        return False

    if text.endswith((".", ",", ";", ":")):
        return False

    alpha = [char for char in text if char.isalpha()]
    if not alpha:
        return False

    upper_ratio = sum(char.isupper() for char in alpha) / len(alpha)
    title_case_words = sum(
        1 for word in text.split()
        if word and word[0].isupper()
    )

    word_count = len(text.split())
    title_ratio = title_case_words / max(1, word_count)

    # Geometry is a secondary signal. It must agree with actual heading-like
    # typography rather than classifying every short OCR line as a heading.
    return (
        upper_ratio >= 0.55
        or title_ratio >= 0.80
        or (word_count <= 2 and title_ratio >= 0.50)
    )


def _y_overlap_ratio(a, b):
    ag = a.get("geometry") or {}
    bg = b.get("geometry") or {}
    if not ag or not bg:
        return 0.0

    overlap = max(
        0.0,
        min(float(ag["y2"]), float(bg["y2"]))
        - max(float(ag["y1"]), float(bg["y1"])),
    )
    denom = max(
        1.0,
        min(float(ag["height"]), float(bg["height"])),
    )
    return overlap / denom


def _horizontal_overlap_ratio(a, b):
    ag = a.get("geometry") or {}
    bg = b.get("geometry") or {}
    if not ag or not bg:
        return 0.0

    overlap = max(
        0.0,
        min(float(ag["x2"]), float(bg["x2"]))
        - max(float(ag["x1"]), float(bg["x1"])),
    )
    denom = max(
        1.0,
        min(float(ag["width"]), float(bg["width"])),
    )
    return overlap / denom


def _has_strong_column_split(left_blocks, right_blocks, image_width):
    """Check whether two x-groups are genuinely separate visual columns."""
    if len(left_blocks) < 2 or len(right_blocks) < 2:
        return False

    # Two real columns normally have text at overlapping vertical positions.
    overlap_pairs = 0
    total_pairs = 0
    for left in left_blocks:
        for right in right_blocks:
            total_pairs += 1
            if _y_overlap_ratio(left, right) >= 0.15:
                overlap_pairs += 1

    if total_pairs == 0:
        return False

    overlap_ratio = overlap_pairs / total_pairs

    left_y1 = min(
        float((block.get("geometry") or {}).get("y1") or 0.0)
        for block in left_blocks
    )
    left_y2 = max(
        float((block.get("geometry") or {}).get("y2") or 0.0)
        for block in left_blocks
    )
    right_y1 = min(
        float((block.get("geometry") or {}).get("y1") or 0.0)
        for block in right_blocks
    )
    right_y2 = max(
        float((block.get("geometry") or {}).get("y2") or 0.0)
        for block in right_blocks
    )

    total_span = max(1.0, max(left_y2, right_y2) - min(left_y1, right_y1))
    common_span = max(
        0.0,
        min(left_y2, right_y2) - max(left_y1, right_y1),
    )
    vertical_span_ratio = common_span / total_span

    return overlap_ratio >= 0.10 and vertical_span_ratio >= 0.18


def _assign_visual_columns(blocks, image_width):
    """
    Infer visual columns adaptively from OCR geometry.

    When the OCR service has already produced a reliable ``layout_column``
    label, preserve it. Otherwise, infer columns from geometry as a fallback.

    This is deliberately domain-agnostic and supports one-column handwritten
    notes, two-column study notes, and multi-panel screenshots.
    """
    # The OCR service already performs a layout pass and may provide reliable
    # column labels. Prefer those labels when they cover most geometric blocks
    # and do not create singleton columns. Re-inference should be a fallback,
    # not a second competing column detector.
    provided = [
        block.get("layout_column")
        for block in blocks
        if block.get("geometry") and block.get("layout_column") is not None
    ]

    geometric_count = sum(
        1
        for block in blocks
        if block.get("geometry")
    )

    if provided and geometric_count > 0:
        coverage = len(provided) / geometric_count
        normalized_labels = []

        for value in provided:
            try:
                normalized_labels.append(int(value))
            except (TypeError, ValueError):
                normalized_labels.append(str(value))

        label_counts = {}
        for label in normalized_labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        valid_labels = (
            1 <= len(label_counts) <= 4
            and all(count >= 2 for count in label_counts.values())
        )

        if coverage >= 0.70 and valid_labels:
            for block in blocks:
                label = block.get("layout_column")
                if label is None:
                    block["visual_column"] = 0
                    continue
                try:
                    block["visual_column"] = int(label)
                except (TypeError, ValueError):
                    block["visual_column"] = str(label)
            return

    geometric = [
        block for block in blocks
        if block.get("geometry")
        and block["geometry"].get("cx") is not None
    ]

    if len(geometric) < 4 or image_width <= 0:
        for block in blocks:
            block["visual_column"] = 0
        return

    ordered = sorted(
        geometric,
        key=lambda item: float(item["geometry"]["cx"]),
    )

    centers = [float(block["geometry"]["cx"]) for block in ordered]
    widths = [
        float(block["geometry"].get("width") or 0.0)
        for block in ordered
        if float(block["geometry"].get("width") or 0.0) > 0
    ]
    median_width = _median(widths, image_width * 0.04)

    # A genuine column gap is usually much wider than a text block and also
    # occupies a meaningful fraction of the image width.
    # Keep the gap test relative to the page width as well as text size.
    # A page can have very wide text boxes in each column; multiplying that
    # width by a large factor would incorrectly suppress a genuine column
    # break.
    gap_threshold = min(
        image_width * 0.18,
        max(image_width * 0.08, median_width * 1.6),
    )

    candidate_indices = [
        index
        for index in range(len(centers) - 1)
        if centers[index + 1] - centers[index] >= gap_threshold
    ]

    if not candidate_indices:
        for block in blocks:
            block["visual_column"] = 0
        return

    # Evaluate candidate cuts, preferring the strongest gaps first.
    candidates = sorted(
        candidate_indices,
        key=lambda index: centers[index + 1] - centers[index],
        reverse=True,
    )[:3]

    accepted = []
    for cut in sorted(candidates):
        left = ordered[: cut + 1]
        right = ordered[cut + 1 :]
        if _has_strong_column_split(left, right, image_width):
            accepted.append(cut)

    if not accepted:
        for block in blocks:
            block["visual_column"] = 0
        return

    # Avoid producing tiny columns.  At most four visual columns are retained.
    boundaries = sorted(set(accepted))
    group_ranges = []
    start = 0
    for boundary in boundaries:
        group_ranges.append(ordered[start : boundary + 1])
        start = boundary + 1
    group_ranges.append(ordered[start:])

    group_ranges = [group for group in group_ranges if group]

    if len(group_ranges) < 2 or len(group_ranges) > 4:
        for block in blocks:
            block["visual_column"] = 0
        return

    for column_id, group in enumerate(group_ranges):
        for block in group:
            block["visual_column"] = column_id

    # Blocks without usable geometry follow their nearest neighboring block.
    for block in blocks:
        if "visual_column" in block:
            continue
        block["visual_column"] = 0


def _same_visual_column(a, b):
    return a.get("visual_column", 0) == b.get("visual_column", 0)


def _spatially_related_to_heading(heading, block, column_blocks, median_height):
    """Decide whether a block plausibly belongs below a heading."""
    hg = heading.get("geometry") or {}
    bg = block.get("geometry") or {}
    if not hg or not bg:
        return True

    # Never pull content located clearly above the heading.
    if float(bg["y1"]) < float(hg["y2"]) - max(2.0, median_height * 0.30):
        return False

    column_width = 0.0
    if column_blocks:
        x1 = min(
            float((item.get("geometry") or {}).get("x1") or 0.0)
            for item in column_blocks
            if item.get("geometry")
        )
        x2 = max(
            float((item.get("geometry") or {}).get("x2") or 0.0)
            for item in column_blocks
            if item.get("geometry")
        )
        column_width = max(1.0, x2 - x1)

    overlap = _horizontal_overlap_ratio(heading, block)
    center_gap = abs(float(bg["cx"]) - float(hg["cx"]))

    horizontal_ok = (
        overlap >= 0.08
        or center_gap <= max(
            column_width * 0.35,
            float(hg["width"]) * 1.6,
        )
    )

    if not horizontal_ok:
        return False

    # Very large vertical gaps are fine for long sections, but an unrelated
    # visually separated region should not be pulled into the section.
    vertical_gap = max(
        0.0,
        float(bg["y1"]) - float(hg["y2"]),
    )
    max_reasonable_gap = max(
        median_height * 8.0,
        column_width * 0.35,
    )

    if vertical_gap > max_reasonable_gap:
        # Keep numbered/bullet content if it still aligns horizontally.  This
        # preserves long handwritten lists while avoiding distant callouts.
        text = str(block.get("text") or "").strip()
        return _is_bullet_item(text) or bool(re.match(r"^\d+[.)]", text))

    return True


def _is_obvious_decorative_fragment(text):
    """Conservative generic detector for OCR-only decorative fragments."""
    stripped = str(text or "").strip()
    if not stripped:
        return True

    if stripped.startswith(("\"", "“", "”", "‘", "’")):
        return True

    # Very short standalone fragments are often pieces of a callout, but keep
    # numbers and bullet items because they can be legitimate list content.
    if len(stripped) <= 5 and not re.match(r"^(?:\d+[.)]?|[•·◦▪‣⁃\-*–—])", stripped):
        return True

    return False


def _clean_list_section_blocks(heading, body_blocks):
    """
    Preserve list items and their wrapped continuations while dropping clearly
    unrelated decorative OCR fragments.

    This does not contain any domain-specific vocabulary.
    """
    if not body_blocks:
        return []

    bullet_blocks = [
        block for block in body_blocks
        if _is_bullet_item(block.get("text"))
    ]

    if len(bullet_blocks) < 2:
        return body_blocks

    ratio = len(bullet_blocks) / max(1, len(body_blocks))
    if ratio < 0.40:
        return body_blocks

    cleaned = []
    median_height = _median(
        [
            (block.get("geometry") or {}).get("height")
            for block in body_blocks
            if block.get("geometry")
        ],
        10.0,
    )

    for block in body_blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue

        if _is_bullet_item(text):
            cleaned.append(block)
            continue

        if _is_obvious_decorative_fragment(text):
            continue

        if not cleaned:
            continue

        previous = cleaned[-1]

        if not _same_visual_column(previous, block):
            continue

        pg = previous.get("geometry") or {}
        bg = block.get("geometry") or {}
        if not pg or not bg:
            continue

        vertical_gap = float(bg["y1"]) - float(pg["y2"])
        x_gap = abs(float(bg["cx"]) - float(pg["cx"]))

        allowed_gap = max(2.0 * median_height, 24.0)
        allowed_x = max(
            float(pg["width"]) * 0.45,
            median_height * 3.0,
        )

        short_fragment = len(text) <= 100
        no_new_heading = not _looks_like_heading(
            block,
            median_height,
        )

        # OCR can drop a bullet from an otherwise valid list item. Preserve
        # aligned non-heading lines when they occur inside the same list
        # rhythm, regardless of capitalization. Requiring a short block,
        # nearby vertical position, and matching column keeps this generic
        # without hard-coding document vocabulary.
        if (
            0.0 <= vertical_gap <= allowed_gap
            and x_gap <= allowed_x
            and short_fragment
            and no_new_heading
        ):
            cleaned.append(block)

    return cleaned


def _split_implicit_sections(column_blocks, image_height):
    """Fallback grouping for columns without recognizable headings."""
    if not column_blocks:
        return []

    heights = [
        (block.get("geometry") or {}).get("height")
        for block in column_blocks
        if block.get("geometry")
    ]
    median_height = _median(heights, max(8.0, image_height * 0.01))
    gap_threshold = max(
        median_height * 2.2,
        image_height * 0.012,
    )

    groups = []
    current = [column_blocks[0]]

    for previous, block in zip(column_blocks, column_blocks[1:]):
        pg = previous.get("geometry") or {}
        bg = block.get("geometry") or {}
        if not pg or not bg:
            current.append(block)
            continue

        gap = float(bg["y1"]) - float(pg["y2"])
        if gap > gap_threshold and len(current) >= 1:
            groups.append(current)
            current = [block]
        else:
            current.append(block)

    if current:
        groups.append(current)

    return groups


def _build_visual_sections(blocks, image_width, image_height):
    """
    Adaptive, domain-agnostic 2-D image layout analysis.

    The algorithm deliberately avoids document-specific rules.  It first
    detects strong visual columns, then detects heading-like blocks inside each
    column, and finally associates nearby text/bullets with that heading.  If a
    layout does not expose reliable headings, it falls back to vertical groups.

    This handles single-column handwriting, multi-column notes, side-by-side
    panels, screenshots, and mixed-layout study images without requiring a new
    extractor rule for each document.
    """
    normalized = []

    for original_index, raw in enumerate(blocks or []):
        if not isinstance(raw, dict):
            continue

        content = str(raw.get("text") or "").strip()
        if not content:
            continue

        geometry = _block_geometry(raw)
        block = dict(raw)
        block["text"] = content
        block["geometry"] = geometry
        block["original_index"] = original_index
        normalized.append(block)

    if not normalized:
        return []

    heights = [
        (block.get("geometry") or {}).get("height")
        for block in normalized
        if block.get("geometry")
    ]
    median_height = _median(heights, max(8.0, image_height * 0.01))

    _assign_visual_columns(normalized, image_width)

    # Mark consecutive numbered procedures/lists before heading detection.
    # This prevents lines such as "1) ...", "2) ...", "3) ..." from being
    # interpreted as three section headings and absorbing the next real heading.
    temporary_columns = {}
    for block in normalized:
        temporary_columns.setdefault(
            block.get("visual_column", 0),
            [],
        ).append(block)

    for column_blocks in temporary_columns.values():
        column_blocks.sort(
            key=lambda item: (
                float((item.get("geometry") or {}).get("y1") or 0.0),
                float((item.get("geometry") or {}).get("x1") or 0.0),
                item.get("original_index", 0),
            )
        )
        _mark_numbered_list_sequences(
            column_blocks,
            median_height,
        )

    # A very wide title/header is treated as a global region rather than being
    # forced into a left/right column.
    for block in normalized:
        geometry = block.get("geometry") or {}
        width = float(geometry.get("width") or 0.0)
        block["is_global"] = (
            image_width > 0
            and width >= image_width * 0.68
            and not _is_bullet_item(block.get("text"))
        )
        block["is_heading"] = _looks_like_heading(
            block,
            median_height,
        )

    columns = {}
    global_blocks = []

    for block in normalized:
        if block.get("is_global"):
            global_blocks.append(block)
        else:
            columns.setdefault(
                block.get("visual_column", 0),
                [],
            ).append(block)

    for column_blocks in columns.values():
        column_blocks.sort(
            key=lambda item: (
                float((item.get("geometry") or {}).get("y1") or 0.0),
                float((item.get("geometry") or {}).get("x1") or 0.0),
                item.get("original_index", 0),
            )
        )

    groups = []

    # Keep a global title/header separate.  This is useful for documents whose
    # actual sections start below the title and also avoids cross-column leaks.
    for block in sorted(
        global_blocks,
        key=lambda item: (
            float((item.get("geometry") or {}).get("y1") or 0.0),
            float((item.get("geometry") or {}).get("x1") or 0.0),
        ),
    ):
        groups.append({
            "heading": None,
            "blocks": [block],
            "first_y": float((block.get("geometry") or {}).get("y1") or 0.0),
            "visual_column": -1,
        })

    for column_id, column_blocks in sorted(columns.items(), key=lambda pair: pair[0]):
        heading_positions = [
            index
            for index, block in enumerate(column_blocks)
            if block.get("is_heading")
        ]

        title_only_index = None
        if len(heading_positions) == 1:
            only_index = heading_positions[0]
            only_heading = column_blocks[only_index]
            only_text = str(only_heading.get("text") or "").strip()
            only_y = float((only_heading.get("geometry") or {}).get("y1") or 0.0)
            title_like = (
                not _is_numbered_heading(only_text)
                and image_height > 0
                and only_y <= image_height * 0.12
            )
            if title_like:
                title_only_index = only_index
                heading_positions = []
                groups.append({
                    "heading": None,
                    "blocks": [only_heading],
                    "first_y": only_y,
                    "visual_column": column_id,
                })

        content_blocks_for_fallback = (
            [
                block
                for index, block in enumerate(column_blocks)
                if index != title_only_index
            ]
            if title_only_index is not None
            else column_blocks
        )

        if heading_positions:
            for position_index, heading_position in enumerate(heading_positions):
                heading = column_blocks[heading_position]
                next_heading_position = (
                    heading_positions[position_index + 1]
                    if position_index + 1 < len(heading_positions)
                    else len(column_blocks)
                )

                candidate_body = column_blocks[
                    heading_position + 1 : next_heading_position
                ]

                section_body = []
                for block in candidate_body:
                    if _spatially_related_to_heading(
                        heading,
                        block,
                        column_blocks,
                        median_height,
                    ):
                        section_body.append(block)

                cleaned_body = _clean_list_section_blocks(
                    heading,
                    section_body,
                )

                final_blocks = [heading] + cleaned_body

                if len(final_blocks) <= 1:
                    continue

                heading_geometry = heading.get("geometry") or {}
                groups.append({
                    "heading": heading,
                    "blocks": final_blocks,
                    "first_y": float(heading_geometry.get("y1") or 0.0),
                    "visual_column": column_id,
                })
        else:
            for implicit_group in _split_implicit_sections(
                content_blocks_for_fallback,
                image_height=image_height,
            ):
                if implicit_group:
                    groups.append({
                        "heading": None,
                        "blocks": implicit_group,
                        "first_y": float(
                            (implicit_group[0].get("geometry") or {}).get("y1") or 0.0
                        ),
                        "visual_column": column_id,
                    })

    # If there are headings, some non-heading blocks can still remain outside
    # a section.  Attach only close blocks to the nearest same-column section;
    # do not globally merge them, which is what caused the earlier leakage.
    consumed_ids = {
        id(block)
        for group in groups
        for block in group.get("blocks") or []
    }

    for column_id, column_blocks in sorted(columns.items(), key=lambda pair: pair[0]):
        leftovers = [
            block
            for block in column_blocks
            if id(block) not in consumed_ids
            and not block.get("is_heading")
        ]

        for block in leftovers:
            if _is_obvious_decorative_fragment(block.get("text")):
                continue

            geometry = block.get("geometry") or {}
            if not geometry:
                continue

            # Attach to the nearest section only when the vertical distance is
            # small and the block remains in the same visual column.
            best_group = None
            best_distance = float("inf")

            for group in groups:
                if group.get("visual_column") != column_id:
                    continue

                group_blocks = group.get("blocks") or []
                if not group_blocks:
                    continue

                last_block = group_blocks[-1]
                last_geometry = last_block.get("geometry") or {}
                if not last_geometry:
                    continue

                if float(geometry.get("y1")) < float(last_geometry.get("y2")):
                    continue

                distance = float(geometry.get("y1")) - float(last_geometry.get("y2"))
                if distance < best_distance:
                    best_distance = distance
                    best_group = group

            if best_group is not None:
                allowed = max(
                    median_height * 4.0,
                    image_height * 0.03,
                )
                if best_distance <= allowed:
                    best_group["blocks"].append(block)
                    consumed_ids.add(id(block))
                    continue

            # Preserve otherwise-unassigned, meaningful OCR as its own compact
            # section instead of dropping it.
            groups.append({
                "heading": None,
                "blocks": [block],
                "first_y": float(geometry.get("y1") or 0.0),
                "visual_column": column_id,
            })
            consumed_ids.add(id(block))

    groups.sort(
        key=lambda group: (
            float(group.get("first_y") or 0.0),
            int(group.get("visual_column", 0)),
        )
    )

    return groups


def _aggregate_group_bbox(group):
    """Create a flat aggregate bbox for a logical section."""
    points = []

    for block in group.get("blocks") or []:
        geometry = block.get("geometry")
        if not geometry:
            continue
        points.extend([
            [geometry["x1"], geometry["y1"]],
            [geometry["x2"], geometry["y1"]],
            [geometry["x2"], geometry["y2"]],
            [geometry["x1"], geometry["y2"]],
        ])

    if not points:
        return None

    x1 = min(point[0] for point in points)
    y1 = min(point[1] for point in points)
    x2 = max(point[0] for point in points)
    y2 = max(point[1] for point in points)

    return [
        [float(x1), float(y1)],
        [float(x2), float(y1)],
        [float(x2), float(y2)],
        [float(x1), float(y2)],
    ]


def _section_content(section):
    """Convert a logical section into clean text while preserving reading order."""
    blocks = section.get("blocks") or []
    if not blocks:
        return "", "OCR Section", []

    heading = section.get("heading")
    heading_text = (
        str(heading.get("text") or "").strip()
        if heading
        else ""
    )

    body = []
    confidences = []
    source_indices = []

    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue

        if heading is not None and block is heading:
            confidences.append(float(block.get("confidence") or 0.0))
            source_indices.append(block.get("original_index"))
            continue

        body.append(text)
        confidences.append(float(block.get("confidence") or 0.0))
        source_indices.append(block.get("original_index"))

    lines = []
    if heading_text:
        lines.append(heading_text)
    lines.extend(body)

    return "\n".join(lines).strip(), (heading_text or "OCR Section"), source_indices


def extract_image(file_path):
    """
    Extract a standalone image into adaptive, layout-aware logical sections.

    Only the JPG/JPEG/PNG path uses this layout logic.  PDF, DOCX, TXT, and
    CSV extraction paths remain unchanged.
    """
    from app.services.ocr_service import ocr_service

    with open(file_path, "rb") as file:
        image_data = file.read()

    try:
        ocr_result = ocr_service.run_ocr_on_image(image_data)

        if not isinstance(ocr_result, dict):
            raise ValueError("OCR service returned an invalid result.")

        ocr_text = str(ocr_result.get("text") or "").strip()
        confidence = float(ocr_result.get("confidence") or 0.0)
        blocks = ocr_result.get("blocks") or []

        if not ocr_text and not blocks:
            raise ValueError("No readable text detected in image.")

        filename = os.path.basename(file_path)
        image_width = int(ocr_result.get("image_width") or 0)
        image_height = int(ocr_result.get("image_height") or 0)

        sections = _build_visual_sections(
            blocks,
            image_width=image_width,
            image_height=image_height,
        )

        image_records = []

        for section_index, section in enumerate(sections):
            content, section_title, source_indices = _section_content(section)
            if not content:
                continue

            section_blocks = section.get("blocks") or []
            section_confidences = [
                float(block.get("confidence") or 0.0)
                for block in section_blocks
                if block.get("text")
            ]
            section_confidence = (
                sum(section_confidences) / len(section_confidences)
                if section_confidences
                else confidence
            )

            metadata = {
                "image_index": section_index,
                "source_type": "image_ocr_section",
                "extraction_method": "ppocrv5_adaptive_layout",
                "ocr_confidence": round(
                    max(0.0, min(section_confidence, 1.0)),
                    3,
                ),
                "section_heading": section_title,
                "ocr_block_count": len(section_blocks),
                "image_width": image_width,
                "image_height": image_height,
            }

            section_bbox = _aggregate_group_bbox(section)
            if section_bbox is not None:
                # ChromaDB-safe representation; exact geometry remains useful
                # for diagnostics without storing a nested metadata structure.
                metadata["bbox"] = str(section_bbox)

            if source_indices:
                metadata["source_block_indices"] = ",".join(
                    str(index)
                    for index in source_indices
                    if index is not None
                )

            visual_column = section.get("visual_column")
            if visual_column is not None:
                metadata["layout_column"] = str(visual_column)

            image_records.append(
                {
                    "content": (
                        f"File Name: {filename}\n"
                        f"[Image OCR Section {section_index + 1}]\n"
                        f"{content}"
                    ),
                    "metadata": metadata,
                }
            )

        # Conservative fallback for genuinely unusual layouts.  Preserve all
        # OCR text as one chunk rather than creating many tiny, unreliable
        # blocks.  This is what makes the extractor resilient to new layouts.
        if not image_records and ocr_text:
            image_records.append(
                {
                    "content": (
                        f"File Name: {filename}\n"
                        "[Image OCR Fallback]\n"
                        f"{ocr_text}"
                    ),
                    "metadata": {
                        "image_index": 0,
                        "source_type": "image_ocr_fallback",
                        "extraction_method": "ppocrv5_fallback",
                        "ocr_confidence": round(
                            max(0.0, min(confidence, 1.0)),
                            3,
                        ),
                        "ocr_block_count": len(blocks),
                        "image_width": image_width,
                        "image_height": image_height,
                    },
                }
            )

        logger.info(
            "[OCR] Image '%s': %d OCR blocks -> %d adaptive sections",
            filename,
            len(blocks),
            len(image_records),
        )

        return {
            # Image content is stored through `images`; keeping top-level text
            # empty avoids creating an extra flattened OCR chunk.
            "text": "",
            "images": image_records,
            "ocr": {
                "confidence": confidence,
                "blocks_count": len(blocks),
                "sections_count": len(image_records),
                "layout_aware": bool(image_records),
            },
        }

    except Exception as error:
        raise ValueError(
            f"Failed to process image with OCR: {error}"
        )

# Text cleanup
def clean_text(text):
    if not text:
        return ""

    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

# Main extractor
def extract_document(
    file_path,
    page_progress_callback=None
):
    """
    Main extraction dispatcher.

    PDF:
        Native text first → OCR fallback

    DOCX:
        Native text + OCR embedded images

    TXT:
        Native extraction

    CSV:
        Tabular extraction

    JPG/JPEG/PNG:
        PaddleOCR
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            "File not found."
        )

    extension = os.path.splitext(
        file_path
    )[1].lower()

    logger.info(
        "[EXTRACTOR] File: %s",
        os.path.basename(file_path)
    )

    logger.info(
        "[EXTRACTOR] Type: %s",
        extension
    )

    images = []

    if extension == ".pdf":
        result = extract_pdf(
            file_path,
            page_progress_callback=page_progress_callback
        )

        text = result["text"]
        images = result["images"]

    elif extension == ".docx":
        result = extract_docx(file_path)

        text = result["text"]
        images.extend(result["images"])

        if page_progress_callback:
            try:
                page_progress_callback(1, 1)
            except Exception:
                pass

    elif extension == ".txt":
        text = extract_txt(file_path)

        if page_progress_callback:
            try:
                page_progress_callback(1, 1)
            except Exception:
                pass

    elif extension == ".csv":
        text = extract_csv(file_path)

        if page_progress_callback:
            try:
                page_progress_callback(1, 1)
            except Exception:
                pass

    elif extension in (
        ".jpg",
        ".jpeg",
        ".png"
    ):
        result = extract_image(file_path)

        text = result["text"]
        images.extend(result["images"])

        if page_progress_callback:
            try:
                page_progress_callback(1, 1)
            except Exception:
                pass

    else:
        raise ValueError(
            "Unsupported file type. "
            "Use PDF, DOCX, TXT, CSV, JPG, JPEG or PNG."
        )

    return {
        "text": clean_text(text),
        "images": images
    }

# Optional standalone text saving
def save_extracted_text(
    text,
    original_file
):
    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    file_name = os.path.splitext(
        os.path.basename(original_file)
    )[0]

    output_file = os.path.join(
        OUTPUT_FOLDER,
        file_name + "_extracted.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(text)

    return output_file

# Standalone testing
def main():
    print("=" * 70)
    print(
        "        AI KNOWLEDGE BASE EXTRACTOR"
    )
    print("=" * 70)

    print("\nSupported formats:")
    print(
        "PDF | DOCX | TXT | CSV | JPG | JPEG | PNG"
    )

    print("\nSelect a file...")

    file_path = select_file()

    if not file_path:
        print("\nNo file selected.")
        return

    print("\nSelected file:")
    print(
        os.path.basename(file_path)
    )

    print("\n" + "=" * 70)
    print("EXTRACTING TEXT")
    print("=" * 70)

    try:
        result = extract_document(
            file_path
        )

        extracted_text = result.get(
            "text",
            ""
        )

        if not extracted_text:
            print(
                "\nNo text could be extracted."
            )
            return

        print(
            "\nExtraction successful!"
        )

        print(
            "Characters extracted:",
            len(extracted_text)
        )

        print("\nExtracted text:")
        print("-" * 70)

        print(
            extracted_text[:5000]
        )

        print("-" * 70)

        output_file = save_extracted_text(
            extracted_text,
            file_path
        )

        print(
            "\nExtracted text saved to:"
        )

        print(
            os.path.abspath(
                output_file
            )
        )

        print(
            "\nExtraction completed successfully."
        )

    except Exception as error:
        print("\nERROR:")
        print(error)


if __name__ == "__main__":
    main()