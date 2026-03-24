# config/file_validation.py
# Validation sécurisée des uploads — recommandations Django + OWASP
# Réf: https://docs.djangoproject.com/en/stable/topics/http/file-uploads/

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False
    logger.warning(
        "python-magic non disponible. Validation MIME désactivée. "
        "Installez: pip install python-magic (et libmagic sur le système)"
    )

# Presets : (extensions, mime_types, max_size_bytes)
DOCUMENT_PRESET = {
    "extensions": {".pdf", ".jpg", ".jpeg", ".png", ".heic"},
    "mime_types": {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    },
    "max_size": 5 * 1024 * 1024,  # 5 Mo
}


def _get_extension(filename: str) -> str:
    """Extrait l'extension en minuscules, avec le point."""
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _get_mime_from_content(uploaded_file) -> Optional[str]:
    """Détecte le type MIME réel via magic bytes (contenu du fichier)."""
    if not MAGIC_AVAILABLE:
        return None
    try:
        chunk = uploaded_file.read(8192)
        uploaded_file.seek(0)
        mime = magic.from_buffer(chunk, mime=True)
        return mime.strip().lower() if mime else None
    except Exception as e:
        logger.warning("Erreur détection MIME: %s", e)
        return None


def validate_upload(
    uploaded_file,
    preset: dict,
    field_name: str = "fichier",
) -> Tuple[bool, Optional[str]]:
    """
    Valide un fichier uploadé : taille, extension, type MIME réel.
    Retourne (True, None) si valide, (False, message_erreur) sinon.
    """
    if not uploaded_file:
        return False, f"{field_name} manquant."

    if not hasattr(uploaded_file, "size") or uploaded_file.size == 0:
        return False, f"{field_name} vide ou manquant."

    if uploaded_file.size > preset["max_size"]:
        max_mb = preset["max_size"] / (1024 * 1024)
        return False, f"{field_name} trop volumineux (max {max_mb:.0f} Mo)."

    ext = _get_extension(getattr(uploaded_file, "name", "") or "")
    if ext not in preset["extensions"]:
        allowed = ", ".join(sorted(preset["extensions"]))
        return False, f"Format non autorisé. Utilisez : {allowed}"

    mime_detected = _get_mime_from_content(uploaded_file)
    if mime_detected:
        if mime_detected not in preset["mime_types"]:
            return False, f"Type de fichier non autorisé (détecté : {mime_detected})."
    else:
        logger.debug("Validation MIME ignorée (magic non dispo), extension seule utilisée")

    return True, None
