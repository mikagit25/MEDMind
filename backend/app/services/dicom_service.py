"""DICOM file processing service.

Converts DICOM (.dcm) files to PNG for web display and extracts
de-identified metadata.  Falls back gracefully when pydicom is not installed
(returns None) so the rest of the app keeps working.

Usage:
    from app.services.dicom_service import dicom_to_png, extract_dicom_metadata

    png_bytes = await dicom_to_png(dcm_bytes)   # None if pydicom unavailable
    meta = extract_dicom_metadata(dcm_bytes)
"""
from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tags to DE-IDENTIFY before returning metadata (HIPAA Safe Harbor)
_PHI_TAGS = {
    "PatientName", "PatientID", "PatientBirthDate", "PatientSex",
    "PatientAge", "PatientWeight", "PatientAddress",
    "InstitutionName", "ReferringPhysicianName", "AccessionNumber",
    "StudyID",
}


def _available() -> bool:
    try:
        import pydicom  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


async def dicom_to_png(dcm_bytes: bytes) -> Optional[bytes]:
    """Convert raw DICOM bytes to PNG bytes suitable for web display.

    Applies VOI LUT / windowing if present in the dataset so the image
    renders with the correct contrast (critical for CT / MRI).
    Runs in asyncio threadpool so it doesn't block the event loop.

    Returns None if pydicom or numpy is not installed.
    """
    if not _available():
        logger.warning("pydicom/numpy not installed — DICOM conversion skipped")
        return None

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _convert_sync, dcm_bytes)


def _convert_sync(dcm_bytes: bytes) -> bytes:
    """Synchronous DICOM → PNG conversion (runs in thread executor)."""
    import numpy as np
    import pydicom
    from PIL import Image
    from pydicom.pixel_data_handlers.util import apply_voi_lut

    ds = pydicom.dcmread(io.BytesIO(dcm_bytes))

    if not hasattr(ds, "pixel_array"):
        raise ValueError("DICOM file has no pixel data")

    pixel_array = ds.pixel_array.astype(float)

    # Apply windowing / VOI LUT when available for correct contrast
    if hasattr(ds, "WindowCenter") and hasattr(ds, "WindowWidth"):
        try:
            pixel_array = apply_voi_lut(ds.pixel_array, ds).astype(float)
        except Exception:
            pass  # fall back to raw pixels

    # Normalise to 0-255
    pmin, pmax = pixel_array.min(), pixel_array.max()
    if pmax > pmin:
        pixel_array = (pixel_array - pmin) / (pmax - pmin) * 255
    img_uint8 = pixel_array.astype(np.uint8)

    # Handle grayscale (2D) and RGB (3D) arrays
    if img_uint8.ndim == 2:
        pil_img = Image.fromarray(img_uint8, mode="L").convert("RGB")
    elif img_uint8.ndim == 3:
        pil_img = Image.fromarray(img_uint8)
    else:
        raise ValueError(f"Unexpected pixel array shape: {img_uint8.shape}")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def extract_dicom_metadata(dcm_bytes: bytes) -> dict:
    """Extract de-identified metadata from a DICOM file.

    PHI fields (PatientName, PatientID, etc.) are removed before returning.
    Safe to log / store in the database.
    """
    if not _available():
        return {"error": "pydicom not installed"}

    import pydicom

    try:
        ds = pydicom.dcmread(io.BytesIO(dcm_bytes), stop_before_pixels=True)
    except Exception as exc:
        return {"error": str(exc)}

    meta: dict = {}
    desired = {
        "Modality": "modality",
        "StudyDescription": "study_description",
        "SeriesDescription": "series_description",
        "BodyPartExamined": "body_part",
        "SliceThickness": "slice_thickness_mm",
        "ImageOrientationPatient": "image_orientation",
        "PixelSpacing": "pixel_spacing_mm",
        "Rows": "rows",
        "Columns": "columns",
        "BitsAllocated": "bits_allocated",
        "WindowCenter": "window_center",
        "WindowWidth": "window_width",
        "Manufacturer": "manufacturer",
        "ManufacturerModelName": "model_name",
    }
    for tag, key in desired.items():
        val = getattr(ds, tag, None)
        if val is not None:
            # Convert pydicom types to plain Python
            if hasattr(val, "__iter__") and not isinstance(val, str):
                val = list(val)
            else:
                val = str(val)
            meta[key] = val

    return meta
