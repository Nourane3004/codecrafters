"""
Source Credibility Agent – Agent de crédibilité de la source
-------------------------------------------------------------
Évalue la fiabilité de la source (domaine, registrar, âge, réputation)
à partir des informations contenues dans le NormalizedFeatureObject.
Sortie : SourceCredibilityResult (score, flags, preuves)
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# =============================================================================
# Modèles de sortie
# =============================================================================

@dataclass
class SourceCredibilityResult:
    """Résultat de l'agent de crédibilité de la source."""
    source_ref: str
    input_type: str                     # IMAGE, URL, DOCUMENT, VIDEO
    domain: Optional[str] = None
    overall_score: float = 0.0          # 0.0 (peu fiable) → 1.0 (très fiable)
    domain_age_days: Optional[int] = None
    registrar_reputation: float = 0.0    # 0-1
    country_risk: float = 0.0            # 0-1 (1 = pays à risque)
    has_ssl: bool = False
    is_known_satire: bool = False
    is_known_fake_news: bool = False
    red_flags: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)   # explications détaillées
    agent_errors: List[str] = field(default_factory=list)


# =============================================================================
# Agent principal
# =============================================================================

class SourceCredibilityAgent:
    """
    Évalue la crédibilité de la source d'information.
    Pour les URLs, analyse le domaine, WHOIS, réputation.
    Pour les images/documents/vidéos, utilise le domaine de téléchargement ou métadonnées.
    """

    # Simule une base de réputation (à remplacer par une vraie API ou base de données)
    _REPUTATION_DB = {
        "example.com": {"score": 0.9, "type": "legitimate"},
        "dubious-news.net": {"score": 0.3, "type": "fake_news"},
        "satire.org": {"score": 0.2, "type": "satire"},
    }

    # Pays considérés à risque (exemple)
    _HIGH_RISK_COUNTRIES = {"RU", "CN", "KP", "IR", "SY", "VE"}

    async def run(self, nfo: Any) -> SourceCredibilityResult:
        """Point d'entrée principal – appelé par le comité d'agents."""
        errors = []
        domain = self._extract_domain(nfo)
        if not domain:
            # Pas de domaine identifiable → score par défaut faible
            return SourceCredibilityResult(
                source_ref=nfo.source_ref,
                input_type=nfo.input_type,
                overall_score=0.3,
                red_flags=["no_domain"],
                evidence=["Impossible d'identifier un nom de domaine pour cette source."],
                agent_errors=[],
            )

        # Récupération des infos WHOIS (simulée)
        whois_info = await self._get_whois_info(domain)
        domain_age = self._compute_domain_age(whois_info.get("creation_date"))

        # Réputation via base interne (ou appel externe)
        reputation = self._REPUTATION_DB.get(domain, {"score": 0.5, "type": "unknown"})
        is_satire = (reputation["type"] == "satire")
        is_fake = (reputation["type"] == "fake_news")

        # Pays à risque
        registrant_country = whois_info.get("registrant_country", "")
        country_risk = 1.0 if registrant_country in self._HIGH_RISK_COUNTRIES else 0.0

        # SSL (simulé – on pourrait vérifier avec une requête réelle)
        has_ssl = await self._check_ssl(domain)

        # Calcul du score global (pondération)
        # Base 0.5, ajustements :
        # +0.2 si domaine âgé > 2 ans
        # +0.2 si réputation > 0.7
        # -0.3 si fake news connu
        # -0.2 si pays à risque
        # -0.1 si pas de SSL
        score = 0.5
        evidence = []

        if domain_age and domain_age > 730:  # > 2 ans
            score += 0.2
            evidence.append(f"Domaine enregistré depuis plus de 2 ans ({domain_age} jours).")
        elif domain_age:
            evidence.append(f"Domaine récent ({domain_age} jours).")

        if reputation["score"] > 0.7:
            score += 0.2
            evidence.append(f"Bonne réputation ({reputation['score']:.2f}).")
        elif reputation["score"] < 0.3:
            score -= 0.3
            evidence.append(f"Mauvaise réputation – {reputation['type']}.")

        if country_risk > 0.5:
            score -= 0.2
            evidence.append(f"Pays d'enregistrement à risque : {registrant_country}.")

        if not has_ssl:
            score -= 0.1
            evidence.append("Site sans certificat SSL valide.")

        score = max(0.0, min(1.0, score))

        red_flags = []
        if is_satire:
            red_flags.append("satire_site")
        if is_fake:
            red_flags.append("known_fake_news")
        if country_risk > 0.5:
            red_flags.append("high_risk_country")

        return SourceCredibilityResult(
            source_ref=nfo.source_ref,
            input_type=nfo.input_type,
            domain=domain,
            overall_score=score,
            domain_age_days=domain_age,
            registrar_reputation=reputation["score"],
            country_risk=country_risk,
            has_ssl=has_ssl,
            is_known_satire=is_satire,
            is_known_fake_news=is_fake,
            red_flags=red_flags,
            evidence=evidence,
            agent_errors=errors,
        )

    def _extract_domain(self, nfo: Any) -> Optional[str]:
        """Extrait le nom de domaine à partir du NFO."""
        if nfo.input_type.value == "url" if hasattr(nfo.input_type, "value") else str(nfo.input_type).upper() == "URL" and nfo.url_data and nfo.url_data.final_url:
            from urllib.parse import urlparse
            parsed = urlparse(nfo.url_data.final_url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        # Pour les autres types, on peut essayer de trouver un domaine dans les métadonnées
        if nfo.input_type.value == "image" if hasattr(nfo.input_type, "value") else str(nfo.input_type).upper() == "IMAGE" and nfo.image_meta and nfo.image_meta.exif:
            # Exemple : exif peut contenir un champ "source" ou "url"
            pass
        return None

    async def _get_whois_info(self, domain: str) -> Dict[str, Any]:
        """
        Simule l'appel WHOIS. À remplacer par une vraie requête (pythonwhois, whois, ou API).
        """
        # Simulation
        await asyncio.sleep(0.01)  # simuler un appel réseau
        # Ici on pourrait interroger une base de données ou API
        return {
            "registrar": "GoDaddy",
            "creation_date": "2015-01-01",
            "expiry_date": "2026-01-01",
            "registrant_country": "US",
            "name_servers": ["ns1.example.com"],
        }

    async def _check_ssl(self, domain: str) -> bool:
        """Vérifie la présence d'un certificat SSL valide pour le domaine."""
        # Simulé – en vrai, utiliser ssl.create_default_context() ou aiohttp
        await asyncio.sleep(0.01)
        return True  # assume SSL présent

    def _compute_domain_age(self, creation_date_str: Optional[str]) -> Optional[int]:
        """Calcule l'âge du domaine en jours depuis la date de création."""
        if not creation_date_str:
            return None
        try:
            creation = datetime.strptime(creation_date_str, "%Y-%m-%d")
            age = (datetime.now() - creation).days
            return max(0, age)
        except Exception:
            return None