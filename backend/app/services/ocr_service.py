import io
import gc
import os
import sys

# Ensure Windows PyTorch DLLs can be loaded by dependencies
if os.name == "nt":
    try:
        import site
        for p in site.getsitepackages():
            tlib = os.path.join(p, "torch", "lib")
            if os.path.exists(tlib):
                try:
                    os.add_dll_directory(tlib)
                except Exception:
                    pass
                os.environ["PATH"] = tlib + ";" + os.environ.get("PATH", "")
    except Exception:
        pass

try:
    import torch
except Exception:
    pass

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_DISABLE_ONEDNN"] = "1"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["FLAGS_enable_pir_onednn"] = "0"

try:
    import paddle
    paddle.set_flags({
        "FLAGS_use_mkldnn": False,
        "FLAGS_enable_pir_api": False,
        "FLAGS_enable_pir_in_executor": False
    })
except Exception:
    pass

import time
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Try importing PyMuPDF (fitz)
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None


class OCRService:
    """
    Lightweight OCR Service using PP-OCRv5 Mobile (PaddleOCR) + PyMuPDF page rendering.
    Designed for deployment on Render Free (CPU, 512MB RAM).
    """

    def __init__(self):
        self._ocr_engine = None

    def _get_ocr_engine(self):
        """Lazy initialization of PP-OCRv5 Mobile engine."""
        if self._ocr_engine is not None:
            return self._ocr_engine

        try:
            if os.name == "nt":
                try:
                    import site
                    for p in site.getsitepackages():
                        tlib = os.path.join(p, "torch", "lib")
                        if os.path.exists(tlib):
                            os.add_dll_directory(tlib)
                except Exception:
                    pass
            from paddleocr import PaddleOCR
        except Exception as e:
            logger.warning(f"[OCR] PaddleOCR import failed ({e}). Falling back to PyMuPDF text extraction.")
            return None

        logger.info("[OCR] Initializing PP-OCRv5 Mobile engine on CPU...")
        try:
            # PP-OCRv5 Mobile / lightweight configuration
            try:
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    enable_mkldnn=False,
                )
            except Exception:
                try:
                    self._ocr_engine = PaddleOCR(
                        use_angle_cls=True,
                        lang="en",
                        enable_onednn=False,
                    )
                except Exception:
                    self._ocr_engine = PaddleOCR(
                        use_angle_cls=True,
                        lang="en",
                    )
            logger.info("[OCR] PP-OCRv5 Mobile engine loaded successfully.")
        except Exception as e:
            logger.error(f"[OCR] Failed to initialize PaddleOCR: {e}")
            self._ocr_engine = None

        return self._ocr_engine

    @staticmethod
    def _box_to_points(box):
        """Normalize PaddleOCR box-like objects into [[x, y], ...]."""
        if box is None:
            return None

        try:
            arr = np.asarray(box, dtype=float)
        except Exception:
            return None

        if arr.size == 0:
            return None

        if arr.ndim == 1 and arr.size >= 4:
            # [x1, y1, x2, y2]
            x1, y1, x2, y2 = arr[:4].tolist()
            return [
                [float(x1), float(y1)],
                [float(x2), float(y1)],
                [float(x2), float(y2)],
                [float(x1), float(y2)],
            ]

        if arr.ndim >= 2 and arr.shape[-1] >= 2:
            points = arr.reshape(-1, arr.shape[-1])[:, :2]
            return [[float(x), float(y)] for x, y in points]

        return None

    @staticmethod
    def _box_stats(box):
        """Return x/y bounds and center for a normalized polygon."""
        if box is None:
            return None
        try:
            if len(box) == 0:
                return None
        except TypeError:
            return None

        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)

        return {
            "x1": float(x1),
            "y1": float(y1),
            "x2": float(x2),
            "y2": float(y2),
            "cx": float((x1 + x2) / 2.0),
            "cy": float((y1 + y2) / 2.0),
            "width": float(max(0.0, x2 - x1)),
            "height": float(max(0.0, y2 - y1)),
        }

    @classmethod
    def _extract_blocks_from_result(cls, result, image_width: int) -> list[dict]:
        """Parse legacy and current PaddleOCR result shapes into text blocks."""
        blocks: list[dict] = []

        if result is None:
            return blocks
        if isinstance(result, np.ndarray) and result.size == 0:
            return blocks
        if isinstance(result, (list, tuple, dict)) and len(result) == 0:
            return blocks

        def add_block(text, confidence, box=None):
            text = str(text or "").strip()
            if not text:
                return

            try:
                score = float(confidence)
            except (TypeError, ValueError):
                score = 0.0

            normalized_box = cls._box_to_points(box)
            stats = cls._box_stats(normalized_box)

            blocks.append({
                "text": text,
                "confidence": max(0.0, min(score, 1.0)),
                "bbox": normalized_box,
                "x1": stats["x1"] if stats else None,
                "y1": stats["y1"] if stats else None,
                "x2": stats["x2"] if stats else None,
                "y2": stats["y2"] if stats else None,
                "cx": stats["cx"] if stats else None,
                "cy": stats["cy"] if stats else None,
                "width": stats["width"] if stats else None,
                "height": stats["height"] if stats else None,
            })

        # Legacy shape: [ [ [box, (text, score)], ... ] ]
        if isinstance(result, list):
            for page_result in result:
                if isinstance(page_result, dict):
                    result = [page_result]
                    break

                if not isinstance(page_result, (list, tuple)):
                    continue

                for line in page_result:
                    if not isinstance(line, (list, tuple)) or len(line) < 2:
                        continue
                    box = line[0]
                    text_tuple = line[1]
                    if isinstance(text_tuple, (list, tuple)) and len(text_tuple) >= 2:
                        add_block(text_tuple[0], text_tuple[1], box)

            if blocks:
                return blocks

        # Current PaddleOCR results may be dictionaries, mapping-like OCRResult
        # objects, or small result objects exposing attributes. Avoid boolean
        # evaluation of NumPy arrays because expressions such as
        # ``array_a or array_b`` raise the ambiguous-truth-value exception.
        result_items = []
        if isinstance(result, dict) or hasattr(result, "get"):
            result_items = [result]
        elif isinstance(result, (list, tuple)):
            result_items = [
                item for item in result
                if isinstance(item, dict) or hasattr(item, "get")
                or any(hasattr(item, attr) for attr in (
                    "rec_texts", "rec_scores", "rec_boxes", "dt_polys",
                    "rec_polys", "boxes"
                ))
            ]

        def get_field(obj, *names):
            for name in names:
                value = None
                if hasattr(obj, "get"):
                    try:
                        value = obj.get(name)
                    except Exception:
                        value = None
                if value is None:
                    try:
                        value = getattr(obj, name, None)
                    except Exception:
                        value = None
                if value is not None:
                    return value
            return None

        def first_nonempty(*values):
            for value in values:
                if value is None:
                    continue
                if isinstance(value, str):
                    if value:
                        return value
                    continue
                try:
                    if len(value) == 0:
                        continue
                except TypeError:
                    pass
                return value
            return None

        for res in result_items:
            rec_texts = first_nonempty(
                get_field(res, "rec_texts"),
                get_field(res, "rec_text"),
            )
            if rec_texts is None:
                rec_texts = []

            rec_scores = first_nonempty(
                get_field(res, "rec_scores"),
                get_field(res, "rec_score"),
            )
            if rec_scores is None:
                rec_scores = []
            boxes = first_nonempty(
                get_field(res, "rec_boxes"),
                get_field(res, "dt_polys"),
                get_field(res, "rec_polys"),
                get_field(res, "boxes"),
            )

            if isinstance(rec_texts, str):
                rec_texts = [rec_texts]
            if isinstance(rec_scores, (int, float, np.integer, np.floating)):
                rec_scores = [rec_scores]

            try:
                text_count = len(rec_texts)
            except TypeError:
                text_count = 0
                rec_texts = []

            try:
                score_count = len(rec_scores)
            except TypeError:
                score_count = 0
                rec_scores = []

            try:
                box_count = len(boxes) if boxes is not None else 0
            except TypeError:
                box_count = 0

            for idx in range(text_count):
                text = rec_texts[idx]
                confidence = rec_scores[idx] if idx < score_count else 0.0
                box = boxes[idx] if boxes is not None and idx < box_count else None
                add_block(text, confidence, box)

        return blocks

    @staticmethod
    def _order_blocks_layout(blocks: list[dict], image_width: int) -> list[dict]:
        """
        Produce a stable reading order while preserving multi-column layouts.

        The algorithm detects large horizontal gaps between text-block centers
        and treats them as column boundaries. Within each detected column,
        blocks are ordered top-to-bottom and then left-to-right.

        If no reliable geometry is available, the original OCR order is kept.
        """
        geometric = [
            block for block in blocks
            if block.get("cx") is not None and block.get("cy") is not None
        ]

        if len(geometric) < 2 or image_width <= 0:
            return blocks

        x_values = sorted(float(block["cx"]) for block in geometric)
        gaps = [x_values[i + 1] - x_values[i] for i in range(len(x_values) - 1)]

        if not gaps:
            return blocks

        # A gap is considered a column boundary only when it is large enough
        # compared with the image width and the typical text-box width.
        widths = [
            float(block.get("width") or 0.0)
            for block in geometric
            if float(block.get("width") or 0.0) > 0
        ]
        median_width = float(np.median(widths)) if widths else image_width * 0.05
        boundary_threshold = max(image_width * 0.10, median_width * 3.0)

        boundaries = [
            index
            for index, gap in enumerate(gaps)
            if gap >= boundary_threshold
        ]

        # Avoid over-partitioning when a page is effectively a single column.
        if not boundaries:
            return sorted(
                blocks,
                key=lambda item: (
                    float(item.get("cy") or 0.0),
                    float(item.get("cx") or 0.0),
                ),
            )

        # Build x-center ranges from the detected gaps.
        groups: list[list[dict]] = []
        current: list[dict] = []

        sorted_geometric = sorted(
            geometric,
            key=lambda item: float(item.get("cx") or 0.0),
        )

        for index, block in enumerate(sorted_geometric):
            current.append(block)
            if index in boundaries:
                groups.append(current)
                current = []
        if current:
            groups.append(current)

        # If a boundary produces implausibly tiny groups, fall back to
        # y-ordering rather than making OCR less stable.
        if len(groups) > 4 or any(len(group) == 1 for group in groups):
            return sorted(
                blocks,
                key=lambda item: (
                    float(item.get("cy") or 0.0),
                    float(item.get("cx") or 0.0),
                ),
            )

        ordered: list[dict] = []
        for group_index, group in enumerate(groups):
            column = sorted(
                group,
                key=lambda item: (
                    float(item.get("cy") or 0.0),
                    float(item.get("cx") or 0.0),
                ),
            )
            for block in column:
                block = dict(block)
                block["layout_column"] = group_index
                ordered.append(block)

        # Preserve any text block for which geometry was unavailable.
        geometric_ids = {id(block) for block in geometric}
        ordered_ids = {id(block) for block in geometric}
        for block in blocks:
            if id(block) not in geometric_ids and id(block) not in ordered_ids:
                ordered.append(dict(block))

        return ordered

    @staticmethod
    def _serialize_layout_blocks(blocks: list[dict]) -> list[str]:
        """Return text lines with lightweight layout markers."""
        lines: list[str] = []
        previous_column = None

        for block in blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue

            column = block.get("layout_column")
            if column is not None and previous_column is not None and column != previous_column:
                lines.append("\n--- Layout Column Break ---")

            if column is not None:
                previous_column = column

            lines.append(text)

        return lines

    def run_ocr_on_image(self, image_bytes: bytes) -> dict:
        """
        Run PaddleOCR on an image and preserve spatial information.

        Returns the legacy `text`/`confidence` fields plus `blocks`, where
        every block contains OCR text, confidence, bounding-box coordinates,
        and an inferred layout column. Existing callers can continue using
        `text` without changes.
        """
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            img_np = np.array(pil_img)
            image_height, image_width = img_np.shape[:2]
        except Exception as e:
            logger.error(f"[OCR] Failed to decode image: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e), "blocks": []}

        ocr_engine = self._get_ocr_engine()
        if ocr_engine is None:
            return {
                "text": "",
                "confidence": 0.0,
                "error": "OCR engine uninitialized",
                "blocks": [],
            }

        try:
            try:
                results = ocr_engine.ocr(img_np)
            except TypeError:
                results = ocr_engine.ocr(img_np, cls=True)

            blocks = self._extract_blocks_from_result(
                results,
                image_width=image_width,
            )

            ordered_blocks = self._order_blocks_layout(
                blocks,
                image_width=image_width,
            )

            confidences = [
                float(block.get("confidence") or 0.0)
                for block in ordered_blocks
                if block.get("text")
            ]

            text_lines = self._serialize_layout_blocks(ordered_blocks)
            full_text = "\n".join(text_lines)
            avg_conf = float(np.mean(confidences)) if confidences else 0.0

            # Expose only stable JSON-like values to callers.
            public_blocks = []
            for block in ordered_blocks:
                public = {
                    "text": block.get("text", ""),
                    "confidence": round(float(block.get("confidence") or 0.0), 3),
                    "bbox": block.get("bbox"),
                    "layout_column": block.get("layout_column"),
                    "x1": block.get("x1"),
                    "y1": block.get("y1"),
                    "x2": block.get("x2"),
                    "y2": block.get("y2"),
                    "cx": block.get("cx"),
                    "cy": block.get("cy"),
                    "width": block.get("width"),
                    "height": block.get("height"),
                }
                public_blocks.append(public)

            return {
                "text": full_text,
                "confidence": round(avg_conf, 3),
                "lines_count": len(text_lines),
                "blocks": public_blocks,
                "image_width": int(image_width),
                "image_height": int(image_height),
            }
        except Exception as e:
            logger.error(f"[OCR] Error during image OCR execution: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e),
                "blocks": [],
            }

    def process_pdf(
        self,
        file_path: str,
        dpi: int = 150,
        page_progress_callback=None
    ) -> dict:
        """
        Processes a PDF by rendering each page using PyMuPDF (fitz) at ~150 DPI,
        running PP-OCRv5 Mobile on each page sequentially, and compiling text & metadata.
        """
        start_time = time.time()
        filename = os.path.basename(file_path)

        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed.")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"[OCR] Failed to open PDF '{filename}': {e}")
            raise ValueError(f"Corrupted or password-protected PDF: {e}")

        num_pages = len(doc)
        logger.info(f"[OCR] Starting PyMuPDF page rendering + PP-OCRv5 for '{filename}' ({num_pages} pages)...")

        pages_data = []
        full_text_blocks = []
        failed_pages = []

        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)

        for page_index in range(num_pages):
            page_num = page_index + 1
            if page_progress_callback:
                page_progress_callback(page_num, num_pages)

            try:
                page = doc.load_page(page_index)

                # Direct PyMuPDF text extraction as fast fallback / hybrid base
                direct_text = page.get_text("text").strip()

                # Render page to 150 DPI image pixmap
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_bytes = pix.tobytes("png")

                # Perform PP-OCRv5 Mobile on rendered page image
                ocr_result = self.run_ocr_on_image(img_bytes)
                ocr_text = ocr_result.get("text", "")
                confidence = ocr_result.get("confidence", 0.0)

                # Clean up page pixmap memory immediately
                del pix
                del img_bytes

                # Combine OCR text and direct text if complementary
                page_text = ocr_text if ocr_text else direct_text
                if ocr_text and direct_text and direct_text not in ocr_text:
                    # Append any missed direct text lines
                    page_text = f"{ocr_text}\n{direct_text}"

                if page_text:
                    page_header = f"--- Page {page_num} (Confidence: {confidence:.2f}) ---"
                    full_text_blocks.append(f"{page_header}\n{page_text}")
                    pages_data.append({
                        "page_number": page_num,
                        "text": page_text,
                        "confidence": confidence,
                        "source": filename,
                        "content_type": "ocr",
                        "extraction_method": "ppocrv5"
                    })
                else:
                    logger.warning(f"[OCR] Page {page_num} yielded no text.")
            except Exception as e:
                logger.error(f"[OCR] Failed to process page {page_num} of '{filename}': {e}")
                failed_pages.append(page_num)
                continue

        doc.close()
        gc.collect()

        total_time = time.time() - start_time
        avg_time_per_page = total_time / max(num_pages, 1)
        full_text = "\n\n".join(full_text_blocks)
        total_chars = len(full_text)

        # Benchmark logging
        logger.info("=" * 60)
        logger.info(f"Document: {filename}")
        logger.info(f"Pages: {num_pages}")
        logger.info(f"OCR time: {total_time:.2f} seconds")
        logger.info(f"Average: {avg_time_per_page:.2f} sec/page")
        logger.info(f"Characters: {total_chars}")
        if failed_pages:
            logger.info(f"Failed pages: {failed_pages}")
        logger.info("=" * 60)

        return {
            "filename": filename,
            "num_pages": num_pages,
            "text": full_text,
            "pages": pages_data,
            "failed_pages": failed_pages,
            "total_time": round(total_time, 2),
            "avg_time_per_page": round(avg_time_per_page, 2),
            "total_characters": total_chars,
        }


# Singleton instance
ocr_service = OCRService()
