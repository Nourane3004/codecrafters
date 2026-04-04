"""
app/pipeline/image/processor.py
================================
Agent Image Forensics — TruthGuard / MENACRAFT

Remplacement complet de l'ancien processor.py.
Conforme aux règles défensives MENACRAFT (handoff v3).

Détecteurs implémentés (libs uniquement depuis requirements.txt) :
  1. ELA  — Error Level Analysis          (Pillow)
  2. EXIF — Métadonnées + incohérences    (Pillow / PIL.ExifTags)
  3. FFT  — Artefacts spectraux GAN       (numpy)
  4. OCR  — Texte embarqué               (PIL → claim_extract)
  5. UI   — Détection de screenshot/meme  (numpy heuristique)

Sortie : NormalizedFeatureObject(source_type="image")
Jamais de raise — dégrade gracieusement avec reasoning_notes.

Dépendances utilisées :
  pillow, numpy  ← déjà dans requirements.txt
  NB : piexif et imagehash NE sont PAS utilisés (absents du projet).
"""

from __future__ import annotations

import hashlib
import io
import os
from typing import Optional

import numpy as np
from PIL import Image, ImageChops, ExifTags

# Imports projet — relatifs à menacraft/ comme working dir
from Preprocessing.app.models.feature_object import NormalizedFeatureObject
from claim_extractor import ExtractedClaim


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

ELA_QUALITY          = 92       # qualité JPEG pour la re-compression ELA
ELA_ANOMALY_RATIO    = 0.05     # fraction de pixels au-dessus du seuil
ELA_PIXEL_THRESHOLD  = 28.0     # seuil de différence par canal (0-255)
ELA_MAX_THRESHOLD    = 75.0     # pic max suspect

FFT_VARIANCE_FLOOR   = 48.0     # variance spectrale minimale d'une vraie photo

EDITING_SOFTWARE = [            # logiciels d'édition (EXIF Software tag)
    "photoshop", "gimp", "lightroom", "affinity",
    "snapseed", "facetune", "meitu", "pixelmator", "darktable",
]

UI_PALETTE_THRESHOLD = 64       # nb max de couleurs uniques → screenshot probable
UI_UNIFORM_RATIO     = 0.30     # ratio de pixels identiques → fond uniforme

CONFIDENCE_BASE      = 0.85
ANOMALY_PENALTY      = 0.10
MAX_TEXT_STORE       = 8000     # NormalizedFeatureObject.extracted_text
MAX_TEXT_LLM         = 12000    # troncature avant Groq


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 1 : Error Level Analysis (ELA)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_ela(img: Image.Image) -> tuple[bool, list[str], Optional[str]]:
    """
    Re-sauvegarde l'image à qualité fixe puis mesure la différence pixel à pixel.
    Les régions manipulées (copy-paste, clone) montrent une erreur anormale
    car elles ont été compressées un nombre différent de fois.

    Retourne : (flag, notes, heatmap_base64_optionnel)
    Pas de heatmap sauvegardée sur disque — conformément à l'architecture
    sans état du projet (tout passe par NormalizedFeatureObject).
    """
    notes: list[str] = []
    flag = False

    try:
        rgb = img.convert("RGB")

        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=ELA_QUALITY)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")

        diff_arr = np.array(ImageChops.difference(rgb, recompressed), dtype=np.float32)

        max_err      = float(diff_arr.max())
        mean_err     = float(diff_arr.mean())
        anomaly_ratio = float((diff_arr > ELA_PIXEL_THRESHOLD).mean())

        if anomaly_ratio > ELA_ANOMALY_RATIO:
            notes.append(
                f"ela_anomaly_ratio: {anomaly_ratio:.2%} des pixels dépassent le seuil "
                f"(seuil={ELA_PIXEL_THRESHOLD}) — région re-compressée probable"
            )
            flag = True

        if max_err > ELA_MAX_THRESHOLD:
            notes.append(
                f"ela_peak_error: pic={max_err:.1f} — artefact de manipulation localisé"
            )
            flag = True

        if not flag:
            notes.append(
                f"ela_ok: anomaly_ratio={anomaly_ratio:.2%} max_err={max_err:.1f} "
                f"mean_err={mean_err:.1f}"
            )

    except Exception as exc:
        notes.append(f"ela_error: {exc}")

    return flag, notes, None


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 2 : EXIF Metadata Forensics (Pillow uniquement)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_exif(img: Image.Image, context: Optional[dict] = None) -> tuple[bool, list[str], dict]:
    """
    Extrait les métadonnées EXIF via Pillow (pas de piexif).
    Détecte : absence d'EXIF, logiciel d'édition, incohérences temporelles.
    """
    notes: list[str] = []
    flag  = False
    meta: dict = {}
    ctx = context or {}

    try:
        raw_exif = img._getexif()   # None si absent
    except Exception:
        raw_exif = None

    if raw_exif is None:
        notes.append(
            "exif_absent: aucune métadonnée EXIF — image éditée, "
            "screenshot, ou générée par IA"
        )
        flag = True
        return flag, notes, meta

    # Décodage des tags
    decoded: dict = {}
    for tag_id, value in raw_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        decoded[tag_name] = value

    meta.update({
        "exif_make":     decoded.get("Make"),
        "exif_model":    decoded.get("Model"),
        "exif_software": decoded.get("Software"),
        "exif_datetime": decoded.get("DateTimeOriginal") or decoded.get("DateTime"),
        "exif_gps":      bool(decoded.get("GPSInfo")),
    })

    # Vérification du logiciel d'édition
    software = (decoded.get("Software") or "").lower()
    if any(kw in software for kw in EDITING_SOFTWARE):
        notes.append(f"exif_editing_software: '{decoded.get('Software')}' détecté")
        flag = True

    # Vérification appareil manquant
    if not decoded.get("Make") and not decoded.get("Model"):
        notes.append("exif_no_device: aucune info appareil dans l'EXIF")
        flag = True

    # Incohérence temporelle avec le contexte de soumission
    dt_orig = decoded.get("DateTimeOriginal") or decoded.get("DateTime")
    if dt_orig and "expected_date" in ctx:
        if ctx["expected_date"] not in str(dt_orig):
            notes.append(
                f"exif_date_mismatch: EXIF={dt_orig!r} "
                f"!= attendu={ctx['expected_date']!r}"
            )
            flag = True

    if not flag:
        notes.append(
            f"exif_ok: make={meta['exif_make']} model={meta['exif_model']} "
            f"dt={meta['exif_datetime']}"
        )

    return flag, notes, meta


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 3 : FFT — Artefacts spectraux GAN / IA (numpy)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_fft_artifact(img: Image.Image) -> tuple[bool, list[str]]:
    """
    Les images générées par GAN ou diffusion présentent des artefacts
    périodiques dans le domaine fréquentiel (grille de convolution, tiling DCT).
    Une faible variance du spectre FFT centré est caractéristique.
    """
    notes: list[str] = []
    flag  = False

    try:
        gray = np.array(img.convert("L"), dtype=np.float32)

        # Redimensionner pour un calcul uniforme
        target = 256
        from PIL import Image as _Img
        gray_img = _Img.fromarray(gray.astype(np.uint8)).resize((target, target))
        gray = np.array(gray_img, dtype=np.float32)

        fft    = np.fft.fft2(gray)
        fshift = np.fft.fftshift(fft)
        mag    = np.log1p(np.abs(fshift))

        # Supprimer le lobe DC central
        cy, cx = mag.shape[0] // 2, mag.shape[1] // 2
        mag[cy - 10:cy + 10, cx - 10:cx + 10] = 0

        variance = float(np.var(mag))

        if variance < FFT_VARIANCE_FLOOR:
            notes.append(
                f"fft_low_variance: {variance:.1f} < seuil={FFT_VARIANCE_FLOOR} "
                "— signature spectrale d'image générée par IA probable"
            )
            flag = True
        else:
            notes.append(f"fft_ok: variance spectrale={variance:.1f}")

    except Exception as exc:
        notes.append(f"fft_error: {exc}")

    return flag, notes


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 4 : UI / Screenshot / Meme Detection (heuristique numpy)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_ui_screenshot(img: Image.Image) -> tuple[bool, list[str], str]:
    """
    Les screenshots et mèmes ne sont pas des photos authentiques.
    Heuristiques : palette réduite, fond uniforme, ratio d'aspect inhabituel.
    Retourne aussi une description textuelle pour claim_extract.
    """
    notes:  list[str] = []
    flag   = False
    desc   = ""

    try:
        arr      = np.array(img.convert("RGB"))
        h, w, _  = arr.shape

        # Palette réduite → screenshot / meme / infographie
        flat        = arr.reshape(-1, 3)
        sample      = flat[::max(1, len(flat) // 5000)]   # subsample
        unique_cols = len(set(map(tuple, sample.tolist())))

        if unique_cols < UI_PALETTE_THRESHOLD:
            notes.append(
                f"ui_reduced_palette: {unique_cols} couleurs uniques "
                f"— screenshot ou image synthétique probable"
            )
            flag = True
            desc = "screenshot_or_synthetic"

        # Fond uniforme (ligne du haut et du bas identiques)
        top_row    = arr[0, :, :]
        bottom_row = arr[-1, :, :]
        top_uniform = float(np.std(top_row)) < 8.0
        bot_uniform = float(np.std(bottom_row)) < 8.0

        if top_uniform and bot_uniform:
            notes.append(
                "ui_uniform_borders: bords horizontaux uniformes — "
                "fond artificiel (meme, infographie, screenshot)"
            )
            flag = True

        # Ratio d'aspect très carré ou très large → meme / bannière
        ratio = w / h if h > 0 else 1.0
        if ratio > 3.5 or ratio < 0.5:
            notes.append(
                f"ui_aspect_ratio: ratio={ratio:.2f} inhabituel pour une photo réelle"
            )

        if not desc:
            desc = f"image {w}x{h} ratio={ratio:.2f}"

    except Exception as exc:
        notes.append(f"ui_detect_error: {exc}")
        desc = "image"

    return flag, notes, desc


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 5 : OCR léger (Pillow — pas de pytesseract requis)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_from_image(img: Image.Image) -> str:
    """
    Extraction de texte embarqué.
    Pillow seul ne fait pas d'OCR — on retourne une description structurée
    qui sera enrichie si pytesseract est disponible en option.
    claim_extract prend en charge le reste via Groq.
    """
    text_parts: list[str] = []

    # Tentative OCR optionnel (pytesseract non requis)
    try:
        import pytesseract   # type: ignore
        ocr_text = pytesseract.image_to_string(img, lang="ara+eng+fra").strip()
        if ocr_text:
            text_parts.append(f"[OCR] {ocr_text}")
    except ImportError:
        pass    # pytesseract absent — pas critique
    except Exception:
        pass

    # Description de fallback si OCR indisponible
    if not text_parts:
        w, h = img.size
        mode = img.mode
        text_parts.append(f"[Image] Résolution : {w}x{h} | Mode : {mode}")

    return " ".join(text_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Score de confiance
# ─────────────────────────────────────────────────────────────────────────────

def _compute_confidence(anomalies: list[str]) -> float:
    score = CONFIDENCE_BASE - len(anomalies) * ANOMALY_PENALTY
    return round(max(0.0, min(1.0, score)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────────

def process(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    context: Optional[dict] = None,
) -> NormalizedFeatureObject:
    """
    Analyse forensique complète d'une image.

    Paramètres
    ----------
    file_bytes : bytes
        Contenu brut de l'image.
    filename : str
        Nom original du fichier.
    mime_type : str
        MIME type détecté par python-magic.
    context : dict, optionnel
        Métadonnées de soumission (expected_date, expected_location, ...).

    Retourne
    --------
    NormalizedFeatureObject(source_type="image")
    Jamais d'exception.
    """
    anomalies:     list[str] = []
    reasoning:     list[str] = []
    metadata:      dict      = {"filename": filename, "mime_type": mime_type}
    agent_results: dict      = {}
    extracted_text: str      = ""
    raw_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        # ── Ouverture Pillow ────────────────────────────────────────────────
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.load()   # forcer le décodage complet maintenant
        except Exception as open_exc:
            reasoning.append(f"image_unreadable: {open_exc}")
            return _build_result(
                anomalies=["image_unreadable"],
                reasoning=reasoning,
                metadata=metadata,
                agent_results={},
                raw_hash=raw_hash,
                extracted_text="",
            )

        # Infos de base
        w, h = img.size
        metadata.update({
            "width":  w,
            "height": h,
            "mode":   img.mode,
            "format": img.format or "unknown",
        })
        reasoning.append(f"image_opened: {w}x{h} {img.mode} ({img.format})")

        # ── Détecteur 1 : ELA ──────────────────────────────────────────────
        flag1, notes1, _ = _detect_ela(img)
        if flag1:
            anomalies.extend(notes1)
        reasoning.extend(notes1)

        # ── Détecteur 2 : EXIF ────────────────────────────────────────────
        flag2, notes2, exif_meta = _detect_exif(img, context=context)
        if flag2:
            anomalies.extend(notes2)
        reasoning.extend(notes2)
        metadata.update(exif_meta)

        # ── Détecteur 3 : FFT ─────────────────────────────────────────────
        flag3, notes3 = _detect_fft_artifact(img)
        if flag3:
            anomalies.extend(notes3)
        reasoning.extend(notes3)

        # ── Détecteur 4 : UI / Screenshot ────────────────────────────────
        flag4, notes4, ui_desc = _detect_ui_screenshot(img)
        if flag4:
            anomalies.extend(notes4)
        reasoning.extend(notes4)

        # ── Détecteur 5 : OCR → texte ─────────────────────────────────────
        ocr_text = _extract_text_from_image(img)
        reasoning.append(
            f"text_extraction: {len(ocr_text)} chars extraits"
        )

        # Constitution du texte final pour claim_extract
        extracted_text = (
            f"[Image forensics] Fichier : {filename} | "
            f"Résolution : {w}x{h} | Format : {img.format} | "
            f"Anomalies : {len(anomalies)} | "
            f"{ui_desc}\n\n"
            f"{ocr_text}"
        )[:MAX_TEXT_LLM]

        # ── Claim extraction (Groq) ────────────────────────────────────────
        try:
            claim_result = ExtractedClaim(
                extracted_text=extracted_text,
                source_type="image",
            )
            # Sérialisation défensive
            try:
                cr_dict = claim_result.__dict__
            except AttributeError:
                cr_dict = dict(claim_result)

            agent_results["claim_extract"] = cr_dict

            if claim_result.high_risk_claims > 0:
                anomalies.append(
                    f"claim_high_risk: {claim_result.high_risk_claims} "
                    "affirmation(s) à risque élevé détectée(s)"
                )
            reasoning.extend(getattr(claim_result, "reasoning_notes", []))

        except Exception as ce:
            reasoning.append(f"claim_extract_error: {ce}")
            agent_results["claim_extract"] = {"error": str(ce)}

    except Exception as top_exc:
        reasoning.append(f"processor_error: {top_exc}")
        anomalies.append("processor_error")

    return _build_result(
        anomalies=anomalies,
        reasoning=reasoning,
        metadata=metadata,
        agent_results=agent_results,
        raw_hash=raw_hash,
        extracted_text=extracted_text,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Construction du NormalizedFeatureObject
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(
    anomalies: list[str],
    reasoning: list[str],
    metadata:  dict,
    agent_results: dict,
    raw_hash:  str,
    extracted_text: str,
) -> NormalizedFeatureObject:
    confidence = _compute_confidence(anomalies)

    obj = NormalizedFeatureObject(
        source_type="image",
        extracted_text=extracted_text[:MAX_TEXT_STORE],
        confidence_score=confidence,
        anomalies_detected=anomalies,
        metadata=metadata,
        reasoning_notes=reasoning,
        raw_bytes_hash=raw_hash,
    )

    # Ajout défensif — agent_results peut ne pas encore exister dans le schéma
    try:
        obj.agent_results = agent_results
    except AttributeError:
        pass

    return obj