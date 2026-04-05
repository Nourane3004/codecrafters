"""
app/pipeline/video/processor.py
================================
Agent Video Forensics & Deepfake Detection — TruthGuard / MENACRAFT

Détecteurs implémentés :
  1. Sharpness variance  (Laplacian) — incohérence de netteté inter-frames
  2. Temporal consistency — sauts brusques de luminosité / flicker
  3. Face-region anomaly — asymétrie + artefacts de bords faciaux (heuristique)
  4. Frequency artifact  — FFT sur patches faciaux (GAN signature)
  5. Metadata forensics  — OpenCV backend + durée / fps suspects
  6. Audio-visual sync   — stub (FaceForensics++ TODO)

Architecture :
  - Conforme aux règles défensives MENACRAFT (jamais de raise, toujours NormalizedFeatureObject)
  - Intègre claim_extract sur la transcription si disponible
  - Temp file nettoyé dans le bloc finally
  - Windows-safe : os.path.join, tempfile

Input  : bytes + filename + mime_type
Output : NormalizedFeatureObject(source_type="video")
"""

from __future__ import annotations

import hashlib
import os
import struct
import tempfile
import time
from typing import Optional

import cv2
import numpy as np

# Import projet — chemins relatifs à menacraft/ comme working dir
from Preprocessing.app.models.feature_object import NormalizedFeatureObject
# FIX: Import ClaimExtractionResult instead of ExtractedClaim (same reason as image agent)
from claim_extractor import ClaimExtractionResult


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

MAX_FRAMES_SAMPLED   = 16       # frames prélevées uniformément
SHARPNESS_THRESHOLD  = 80.0     # variance Laplacian min pour une frame nette
FLICKER_THRESHOLD    = 25.0     # saut de luminosité moyen acceptable (0-255)
FACE_EDGE_THRESHOLD  = 0.18     # ratio bords faciaux anormaux
FFT_VARIANCE_FLOOR   = 45.0     # variance spectrale min d'une vraie caméra
CONFIDENCE_BASE      = 0.85
ANOMALY_PENALTY      = 0.10


# ─────────────────────────────────────────────────────────────────────────────
# Structures internes
# ─────────────────────────────────────────────────────────────────────────────

class FrameStats:
    """Statistiques extraites d'une seule frame."""

    def __init__(self, index: int, timestamp_s: float, frame: np.ndarray):
        self.index        = index
        self.timestamp_s  = timestamp_s
        gray              = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.sharpness    = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        self.mean_lum     = float(gray.mean())
        self.frame        = frame
        self.gray         = gray


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 1 : Sharpness Variance
# ─────────────────────────────────────────────────────────────────────────────

def _detect_sharpness_anomaly(stats: list[FrameStats]) -> tuple[bool, list[str]]:
    """
    Une vraie vidéo présente une variance de netteté cohérente.
    Un deepfake par insertion de frames synthétiques crée des pics/creux brusques.
    """
    notes: list[str] = []
    sharpness_vals = [s.sharpness for s in stats]

    if len(sharpness_vals) < 2:
        return False, notes

    std_sharp = float(np.std(sharpness_vals))
    mean_sharp = float(np.mean(sharpness_vals))

    # Frames flous isolés (synthetic insert)
    blurry_frames = [s.index for s in stats if s.sharpness < SHARPNESS_THRESHOLD]
    sharp_ratio   = len(blurry_frames) / len(stats)

    flag = False

    if sharp_ratio > 0.4:
        notes.append(
            f"sharpness_global_low: {sharp_ratio:.0%} des frames sont floues "
            f"(mean={mean_sharp:.1f})"
        )
        flag = True

    if std_sharp > mean_sharp * 1.2 and mean_sharp > 0:
        notes.append(
            f"sharpness_high_variance: std={std_sharp:.1f} >> mean={mean_sharp:.1f} "
            "— incohérence suspecte entre frames"
        )
        flag = True

    return flag, notes


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 2 : Temporal Consistency (Luminosity Flicker)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_temporal_inconsistency(stats: list[FrameStats]) -> tuple[bool, list[str]]:
    """
    Les deepfakes montrent souvent un flicker de luminosité entre frames
    synthétiques et frames réelles (le GAN ne génère pas frame par frame).
    """
    notes: list[str] = []

    if len(stats) < 3:
        return False, notes

    lum_vals = [s.mean_lum for s in stats]
    diffs    = [abs(lum_vals[i+1] - lum_vals[i]) for i in range(len(lum_vals) - 1)]
    mean_diff = float(np.mean(diffs))
    max_diff  = float(np.max(diffs))

    flag = False

    if mean_diff > FLICKER_THRESHOLD:
        notes.append(
            f"temporal_flicker_high: luminosité moyenne change de {mean_diff:.1f}/frame "
            f"(seuil={FLICKER_THRESHOLD})"
        )
        flag = True

    if max_diff > FLICKER_THRESHOLD * 3:
        notes.append(
            f"temporal_spike: saut brutal de luminosité {max_diff:.1f} "
            f"à la frame {diffs.index(max_diff) + 1}"
        )
        flag = True

    return flag, notes


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 3 : Face-Region Edge Anomaly (heuristique sans dlib)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_face_edge_anomaly(stats: list[FrameStats]) -> tuple[bool, list[str]]:
    """
    Les deepfakes par face-swap laissent des artefacts de bords dans la région
    faciale : gradient élevé à la jointure visage/fond.
    Heuristique légère sans dlib : détection Haar + analyse Canny dans ROI.

    FaceForensics++ PyTorch model = TODO stub (voir commentaire en bas).
    """
    notes: list[str] = []
    flag  = False

    # Charger le classificateur Haar depuis OpenCV
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    if face_cascade.empty():
        notes.append("face_cascade_unavailable: détection faciale désactivée")
        return False, notes

    anomalous_frames  = 0
    frames_with_faces = 0

    for s in stats:
        faces = face_cascade.detectMultiScale(
            s.gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )

        if len(faces) == 0:
            continue

        frames_with_faces += 1

        for (x, y, w, h) in faces[:1]:   # on analyse le visage principal seulement
            # Agrandir le ROI de 20% pour capturer les bords de fusion
            margin = int(max(w, h) * 0.20)
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(s.gray.shape[1], x + w + margin)
            y2 = min(s.gray.shape[0], y + h + margin)

            roi = s.gray[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            edges = cv2.Canny(roi, threshold1=50, threshold2=150)
            edge_ratio = float(edges.sum() / 255) / roi.size

            if edge_ratio > FACE_EDGE_THRESHOLD:
                anomalous_frames += 1

    if frames_with_faces > 0:
        ratio = anomalous_frames / frames_with_faces
        if ratio > 0.35:
            notes.append(
                f"face_edge_anomaly: {ratio:.0%} des frames avec visage montrent "
                f"des artefacts de bords suspects (face-swap boundary)"
            )
            flag = True

    # ── TODO : FaceForensics++ PyTorch stub ──────────────────────────────────
    # from app.models.faceforensics import FaceForensicsModel
    # ff_model = FaceForensicsModel.load("weights/ff++_c23.pth")
    # for s in stats:
    #     faces = face_cascade.detectMultiScale(s.gray, ...)
    #     if len(faces):
    #         x, y, w, h = faces[0]
    #         roi_bgr = s.frame[y:y+h, x:x+w]
    #         roi_tensor = preprocess(roi_bgr)
    #         pred = ff_model(roi_tensor)  # → (real_prob, fake_prob)
    #         if pred["fake_prob"] > 0.7:
    #             flag = True
    # ─────────────────────────────────────────────────────────────────────────

    return flag, notes


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 4 : Frequency Artifact — FFT sur patch facial
# ─────────────────────────────────────────────────────────────────────────────

def _detect_fft_artifact(stats: list[FrameStats]) -> tuple[bool, list[str]]:
    """
    Les images synthétiques GAN/diffusion présentent des artefacts périodiques
    dans le domaine fréquentiel (grille DCT, tiling de convolution).
    On analyse la variance du spectre FFT centré sur la région faciale.
    """
    notes: list[str] = []
    flag  = False

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    if face_cascade.empty():
        return False, notes

    variances: list[float] = []

    for s in stats[::2]:   # une frame sur deux suffit pour FFT
        faces = face_cascade.detectMultiScale(
            s.gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        if len(faces) == 0:
            continue

        x, y, w, h = faces[0]
        roi = s.gray[y:y+h, x:x+w]
        if roi.size == 0:
            continue

        roi_resized = cv2.resize(roi, (128, 128))
        fft         = np.fft.fft2(roi_resized.astype(np.float32))
        fshift      = np.fft.fftshift(fft)
        magnitude   = np.log1p(np.abs(fshift))

        # Supprimer le lobe central DC (basse fréquence naturelle)
        cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
        magnitude[cy-8:cy+8, cx-8:cx+8] = 0

        variances.append(float(np.var(magnitude)))

    if variances:
        mean_var = float(np.mean(variances))
        if mean_var < FFT_VARIANCE_FLOOR:
            notes.append(
                f"fft_low_variance: variance spectrale faciale={mean_var:.1f} "
                f"< seuil={FFT_VARIANCE_FLOOR} — signature GAN probable"
            )
            flag = True

    return flag, notes


# ─────────────────────────────────────────────────────────────────────────────
# Détecteur 5 : Metadata Forensics
# ─────────────────────────────────────────────────────────────────────────────

def _extract_video_metadata(cap: cv2.VideoCapture, filename: str) -> tuple[dict, list[str]]:
    """
    Extrait les métadonnées OpenCV et détecte les incohérences suspectes.
    """
    notes: list[str] = []
    meta: dict = {}

    fps          = cap.get(cv2.CAP_PROP_FPS)
    frame_count  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s   = frame_count / fps if fps > 0 else 0.0
    codec_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

    try:
        codec_str = "".join([chr((codec_fourcc >> 8 * i) & 0xFF) for i in range(4)])
    except Exception:
        codec_str = "unknown"

    meta.update({
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_s": round(duration_s, 2),
        "codec": codec_str,
        "filename": filename,
    })

    # Vérifications d'anomalies
    if fps <= 0 or fps > 120:
        notes.append(f"metadata_fps_suspect: fps={fps}")

    if frame_count <= 0:
        notes.append("metadata_no_frames: vidéo vide ou illisible")

    if width == 0 or height == 0:
        notes.append("metadata_invalid_resolution: résolution nulle")

    # FPS non-standard (deepfakes réexportés changent souvent le fps)
    standard_fps = {24, 25, 30, 48, 50, 60}
    if fps > 0 and round(fps) not in standard_fps:
        notes.append(
            f"metadata_nonstandard_fps: {fps:.2f} — réexport/conversion probable"
        )

    return meta, notes


# ─────────────────────────────────────────────────────────────────────────────
# Sampling des frames
# ─────────────────────────────────────────────────────────────────────────────

def _sample_frames(cap: cv2.VideoCapture, n: int = MAX_FRAMES_SAMPLED) -> list[FrameStats]:
    """
    Prélève n frames uniformément réparties dans la vidéo.
    Retourne une liste de FrameStats. N'élève jamais d'exception.
    """
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps         = cap.get(cv2.CAP_PROP_FPS) or 25.0
    stats: list[FrameStats] = []

    if frame_count <= 0:
        return stats

    indices = np.linspace(0, frame_count - 1, min(n, frame_count), dtype=int)

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        timestamp = float(idx) / fps
        try:
            stats.append(FrameStats(index=int(idx), timestamp_s=timestamp, frame=frame))
        except Exception:
            continue

    return stats


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
) -> NormalizedFeatureObject:
    """
    Analyse forensique complète d'une vidéo.

    Paramètres
    ----------
    file_bytes : bytes
        Contenu brut de la vidéo.
    filename : str
        Nom original du fichier (pour les logs et la détection d'extension).
    mime_type : str
        MIME type détecté par python-magic.

    Retourne
    --------
    NormalizedFeatureObject(source_type="video")
    Jamais d'exception — dégrade gracieusement avec error dans reasoning_notes.
    """
    tmp_path: Optional[str] = None
    anomalies:    list[str] = []
    reasoning:    list[str] = []
    metadata:     dict      = {}
    agent_results: dict     = {}

    raw_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        # ── Écriture dans un fichier temporaire (Windows-safe) ─────────────
        suffix = os.path.splitext(filename)[-1] or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # ── Ouverture OpenCV ────────────────────────────────────────────────
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            reasoning.append("video_unreadable: OpenCV ne peut pas décoder ce fichier")
            return _build_result(
                anomalies=["video_unreadable"],
                reasoning=reasoning,
                metadata={"filename": filename, "mime_type": mime_type},
                agent_results={},
                raw_hash=raw_hash,
                extracted_text="",
            )

        # ── Détecteur 5 : Métadonnées ───────────────────────────────────────
        meta, meta_notes = _extract_video_metadata(cap, filename)
        metadata.update(meta)
        metadata["mime_type"] = mime_type
        anomalies.extend(meta_notes)
        reasoning.extend(meta_notes)

        # ── Sampling des frames ─────────────────────────────────────────────
        frame_stats = _sample_frames(cap, n=MAX_FRAMES_SAMPLED)
        cap.release()

        reasoning.append(
            f"frames_sampled: {len(frame_stats)} / {meta.get('frame_count', '?')} "
            f"({meta.get('duration_s', '?')}s @ {meta.get('fps', '?')}fps)"
        )

        if not frame_stats:
            anomalies.append("no_frames_decoded")
            reasoning.append("no_frames_decoded: aucune frame lisible")
        else:
            # ── Détecteur 1 : Sharpness ────────────────────────────────────
            flag1, notes1 = _detect_sharpness_anomaly(frame_stats)
            if flag1:
                anomalies.extend(notes1)
            reasoning.extend(notes1)

            # ── Détecteur 2 : Temporal flicker ────────────────────────────
            flag2, notes2 = _detect_temporal_inconsistency(frame_stats)
            if flag2:
                anomalies.extend(notes2)
            reasoning.extend(notes2)

            # ── Détecteur 3 : Face edge anomaly ───────────────────────────
            flag3, notes3 = _detect_face_edge_anomaly(frame_stats)
            if flag3:
                anomalies.extend(notes3)
            reasoning.extend(notes3)

            # ── Détecteur 4 : FFT artefacts ───────────────────────────────
            flag4, notes4 = _detect_fft_artifact(frame_stats)
            if flag4:
                anomalies.extend(notes4)
            reasoning.extend(notes4)

        # ── Transcription (stub) ────────────────────────────────────────────
        # En production : intégrer Whisper openai-whisper ou faster-whisper
        # transcript = whisper_model.transcribe(tmp_path)["text"]
        # Pour l'instant : description textuelle sommaire pour claim_extract
        extracted_text = (
            f"[Vidéo] Fichier : {filename} | "
            f"Durée : {meta.get('duration_s', '?')}s | "
            f"Résolution : {meta.get('width')}x{meta.get('height')} | "
            f"FPS : {meta.get('fps')} | "
            f"Codec : {meta.get('codec')} | "
            f"Frames analysées : {len(frame_stats)} | "
            f"Anomalies détectées : {len(anomalies)}"
        )

        # ── Claim extraction (Groq) ─────────────────────────────────────────
        # FIX: was instantiating ExtractedClaim with (extracted_text, source_type)
        # kwargs that don't exist on the single-claim model. Use ClaimExtractionResult.
        try:
            claim_result = ClaimExtractionResult(
                success=True,
                extraction_method="heuristic",
                reasoning_notes=[f"video_forensics stub for {filename}"],
            )
            agent_results["claim_extract"] = claim_result.model_dump()

            if claim_result.high_risk_claims > 0:
                anomalies.append(
                    f"claim_high_risk: {claim_result.high_risk_claims} affirmation(s) à risque élevé"
                )
            reasoning.extend(claim_result.reasoning_notes)

        except Exception as ce:
            reasoning.append(f"claim_extract_error: {ce}")
            agent_results["claim_extract"] = {"error": str(ce)}

    except Exception as top_exc:
        reasoning.append(f"processor_error: {top_exc}")
        anomalies.append("processor_error")

    finally:
        # Nettoyage garanti du fichier temporaire (Windows-safe)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return _build_result(
        anomalies=anomalies,
        reasoning=reasoning,
        metadata=metadata,
        agent_results=agent_results,
        raw_hash=raw_hash,
        extracted_text=extracted_text if "extracted_text" in dir() else "",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Construction du NormalizedFeatureObject
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(
    anomalies: list[str],
    reasoning: list[str],
    metadata: dict,
    agent_results: dict,
    raw_hash: str,
    extracted_text: str,
) -> NormalizedFeatureObject:
    confidence = _compute_confidence(anomalies)

    # FIX: input_type and source_ref are required fields on NormalizedFeatureObject.
    # The original code omitted them, causing a Pydantic ValidationError at runtime.
    base = NormalizedFeatureObject(
        input_type="video",                        # FIXED: was missing
        source_ref=metadata.get("filename", ""),   # FIXED: was missing
        source_type="video",
        extracted_text=extracted_text[:8000],      # limite contractuelle
        confidence_score=confidence,
        anomalies_detected=anomalies,
        metadata=metadata,
        reasoning_notes=reasoning,
        raw_bytes_hash=raw_hash,
    )

    # Ajout defensif de agent_results (le champ peut ne pas encore exister)
    try:
        base.agent_results = agent_results
    except AttributeError:
        pass

    return base