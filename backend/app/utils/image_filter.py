import io
import hashlib
from PIL import Image, ImageStat
import logging

logger = logging.getLogger(__name__)

# Minimum dimension thresholds
MIN_WIDTH = 64
MIN_HEIGHT = 64
MIN_AREA = 4096  # 64 x 64
MAX_ASPECT_RATIO = 10.0  # Filter extreme line rules/dividers
MIN_STD_DEV = 5.0  # Filter solid color / blank blocks


def get_image_hash(image: Image.Image) -> str:
    """
    Computes a perceptual/downsampled hash for cross-page image matching.
    Resize to 16x16 grayscale to be resilient to tiny compression differences.
    """
    try:
        small_img = image.convert("L").resize((16, 16), Image.Resampling.BILINEAR)
        pixels = list(small_img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return hashlib.md5(bits.encode("utf-8")).hexdigest()
    except Exception:
        # Fallback to raw MD5 of pixel data
        return hashlib.md5(image.tobytes()).hexdigest()


def is_valid_document_image(
    image_bytes: bytes,
    page_number: int = 1,
    page_hashes_map: dict = None,
) -> tuple[bool, str]:
    """
    Inspects image properties to skip tiny/repeated watermark/logo images
    and identical cross-page icons, while preserving handwritten notes,
    diagrams, equations, tables, graphs, figures, and document images.

    Returns (is_valid: bool, reason: str).
    """
    if not image_bytes or len(image_bytes) < 100:
        return False, "corrupted_or_empty_bytes"

    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size

        # 1. Inspect image dimensions
        if width < MIN_WIDTH or height < MIN_HEIGHT or (width * height) < MIN_AREA:
            return False, f"too_small_{width}x{height}"

        # 2. Inspect aspect ratio
        aspect_ratio = max(width / max(height, 1), height / max(width, 1))
        if aspect_ratio > MAX_ASPECT_RATIO:
            return False, f"extreme_aspect_ratio_{aspect_ratio:.1f}"

        # 3. Inspect color variance (skip solid white/black/gray boxes)
        if image.mode != "RGB":
            rgb_img = image.convert("RGB")
        else:
            rgb_img = image

        stat = ImageStat.Stat(rgb_img)
        std_dev = sum(stat.stddev) / len(stat.stddev)
        if std_dev < MIN_STD_DEV:
            return False, f"low_variance_solid_color_std_{std_dev:.1f}"

        # 4. Inspect cross-page duplicates (watermarks / scanner logos)
        if page_hashes_map is not None:
            img_hash = get_image_hash(image)
            if img_hash not in page_hashes_map:
                page_hashes_map[img_hash] = set()

            pages_seen = page_hashes_map[img_hash]
            pages_seen.add(page_number)

            # If the exact same logo/watermark image appears across more than 2 distinct pages
            if len(pages_seen) > 2:
                return False, f"repeated_cross_page_watermark_seen_{len(pages_seen)}_pages"

        return True, "valid_document_image"

    except Exception as e:
        logger.warning(f"Error inspecting image for page {page_number}: {e}")
        # Defensively default to keeping image if inspection fails
        return True, "inspection_failed_kept_by_default"
