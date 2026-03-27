# Pipeline d’upload pour les pièces jointes de demande : magic bytes, normalisation, stockage sûr.
import io
import logging
import uuid
from typing import Dict, Optional, Set, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _

from config.file_validation import (
    DOCUMENT_PRESET,
    MAGIC_AVAILABLE,
    _get_extension,
    _get_mime_from_content,
)

logger = logging.getLogger(__name__)

MIME_TO_PROCESS: Dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/heic": "heif",
    "image/heif": "heif",
}

_EXT_TO_FALLBACK_MIME: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heif",
}

MIME_ALLOWED_EXT: Dict[str, Set[str]] = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/heic": {".heic"},
    "image/heif": {".heic"},
}


def _require_magic() -> bool:
    return getattr(settings, "FILE_VALIDATION_REQUIRE_MAGIC", not settings.DEBUG)


def _mime_matches_extension(mime: str, ext: str) -> bool:
    allowed = MIME_ALLOWED_EXT.get(mime)
    return bool(allowed and ext in allowed)


def _register_heif_if_needed() -> bool:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        return True
    except ImportError:
        return False


_HEIF_REGISTERED = False


def _ensure_heif():
    global _HEIF_REGISTERED
    if _HEIF_REGISTERED:
        return True
    _HEIF_REGISTERED = _register_heif_if_needed()
    return _HEIF_REGISTERED


def _sanitize_jpeg(raw: bytes) -> bytes:
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92, optimize=True, subsampling="4:2:0")
    return out.getvalue()


def _sanitize_png(raw: bytes) -> bytes:
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    out = io.BytesIO()
    if img.mode == "P" and "transparency" in img.info:
        img = img.convert("RGBA")
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _sanitize_heif_to_jpeg(raw: bytes) -> bytes:
    from PIL import Image, ImageOps

    if not _ensure_heif():
        raise ValueError("HEIC indisponible sur le serveur (pillow-heif / libheif).")
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92, optimize=True, subsampling="4:2:0")
    return out.getvalue()


def _validate_pdf_bytes(raw: bytes) -> bytes:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if not raw.startswith(b"%PDF"):
        raise ValueError(_("Fichier PDF invalide."))
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
    except PdfReadError as e:
        raise ValueError(_("Fichier PDF invalide ou corrompu.")) from e
    if reader.is_encrypted:
        raise ValueError(_("Les PDF protégés ne sont pas acceptés."))
    try:
        page_count = len(reader.pages)
    except PdfReadError as e:
        raise ValueError(_("Fichier PDF invalide ou corrompu.")) from e
    if page_count < 1:
        raise ValueError(_("Fichier PDF invalide ou corrompu."))
    return raw


def process_demand_upload(
    uploaded_file,
    preset: dict,
    field_name: str,
) -> Tuple[Optional[ContentFile], Optional[str]]:
    """
    Valide (taille, extension, magic si requis), désinfecte images / contrôle PDF,
    retourne un ContentFile nommé {uuid}.{ext} ou (None, message d'erreur).
    """
    if not uploaded_file:
        return None, f"{field_name} manquant."

    if not hasattr(uploaded_file, "size") or uploaded_file.size == 0:
        return None, f"{field_name} vide ou manquant."

    if uploaded_file.size > preset["max_size"]:
        max_mb = preset["max_size"] / (1024 * 1024)
        return None, f"{field_name} trop volumineux (max {max_mb:.0f} Mo)."

    name = getattr(uploaded_file, "name", "") or ""
    ext = _get_extension(name)
    if ext not in preset["extensions"]:
        allowed = ", ".join(sorted(preset["extensions"]))
        return None, _("Format non autorisé. Utilisez : {allowed}").format(allowed=allowed)

    req_magic = _require_magic()
    if req_magic and not MAGIC_AVAILABLE:
        logger.error("FILE_VALIDATION_REQUIRE_MAGIC actif mais python-magic indisponible.")
        return None, _("Erreur de configuration du serveur d'envoi (vérifiez libmagic).")

    mime = _get_mime_from_content(uploaded_file)

    if req_magic:
        if not mime:
            return None, _("Type de fichier indéterminé. Veuillez envoyer un autre fichier.")
        if mime not in preset["mime_types"]:
            return None, _("Type non autorisé (détecté : {t}).").format(t=mime)
        if not _mime_matches_extension(mime, ext):
            return None, _("Le contenu ne correspond pas à l'extension du fichier.")
    else:
        if MAGIC_AVAILABLE and mime and mime not in preset["mime_types"]:
            return None, _("Type non autorisé (détecté : {t}).").format(t=mime)
        if MAGIC_AVAILABLE and mime and not _mime_matches_extension(mime, ext):
            return None, _("Le contenu ne correspond pas à l'extension du fichier.")

    raw = uploaded_file.read()
    if len(raw) > preset["max_size"]:
        max_mb = preset["max_size"] / (1024 * 1024)
        return None, f"{field_name} trop volumineux (max {max_mb:.0f} Mo)."

    effective_mime = mime
    if not effective_mime and not req_magic:
        effective_mime = _EXT_TO_FALLBACK_MIME.get(ext)
    if not effective_mime:
        return None, _("Impossible de traiter ce fichier.")

    kind = MIME_TO_PROCESS.get(effective_mime)
    if not kind:
        return None, _("Type non pris en charge: {t}.").format(t=effective_mime)

    try:
        if kind == "pdf":
            out_bytes = _validate_pdf_bytes(raw)
            out_ext = ".pdf"
        elif kind == "jpeg":
            out_bytes = _sanitize_jpeg(raw)
            out_ext = ".jpg"
        elif kind == "png":
            out_bytes = _sanitize_png(raw)
            out_ext = ".png"
        elif kind == "heif":
            out_bytes = _sanitize_heif_to_jpeg(raw)
            out_ext = ".jpg"
        else:
            return None, _("Type non pris en charge.")
    except ValueError as e:
        return None, str(e)
    except Exception:
        logger.exception("Échec traitement upload (%s)", field_name)
        return None, _("Fichier illisible ou corrompu.")

    if len(out_bytes) > preset["max_size"]:
        max_mb = preset["max_size"] / (1024 * 1024)
        return None, f"{field_name} trop volumineux après traitement (max {max_mb:.0f} Mo)."

    new_name = f"{uuid.uuid4().hex}{out_ext}"
    return ContentFile(out_bytes, name=new_name), None
