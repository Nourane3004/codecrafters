"""
Context Agent – Agent de contexte et raisonnement temporel
-----------------------------------------------------------
Vérifie la cohérence des allégations extraites avec une base de connaissances
(graphe de connaissances, temporalité, faits établis).
Utilise une API comme Wikidata ou un graphe interne.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# On réutilise les structures de claim_extractor
from claim_extractor import ExtractedClaim


# =============================================================================
# Modèles de sortie
# =============================================================================

@dataclass
class ContextCheck:
    """Vérification individuelle pour une allégation."""
    claim_text: str
    claim_id: int
    is_consistent: bool           # True si cohérent avec la base de connaissances
    confidence: float             # 0-1
    supporting_facts: List[str]   # extraits de la base de connaissances
    contradicting_facts: List[str]
    temporal_issues: List[str]    # par ex. "La date de l'événement est antérieure à la création de l'entité"
    agent_errors: List[str]

@dataclass
class ContextAgentResult:
    """Résultat global de l'agent de contexte."""
    source_ref: str
    input_type: str
    overall_consistency_score: float          # moyenne des is_consistent pondérée
    temporal_coherence_score: float           # score dédié à la temporalité
    checks: List[ContextCheck] = field(default_factory=list)
    agent_errors: List[str] = field(default_factory=list)


# =============================================================================
# Agent principal
# =============================================================================

class ContextAgent:
    """
    Agent de contexte utilisant un graphe de connaissances (ex. Wikidata)
    et un raisonnement temporel pour évaluer la plausibilité des allégations.
    """

    def __init__(
        self,
        wikidata_api_url: str = "https://www.wikidata.org/wiki/Special:EntityData",
        use_mock: bool = True,                # Pour développement sans API externe
        timeout: float = 10.0,
    ):
        self.wikidata_api_url = wikidata_api_url
        self.use_mock = use_mock
        self.timeout = timeout

    async def run(self, nfo: Any, claims: List[ExtractedClaim]) -> ContextAgentResult:
        """
        Exécute l'agent de contexte.
        Nécessite les allégations extraites (peut être appelé après ClaimExtractor).
        """
        errors = []
        checks = []

        if not claims:
            return ContextAgentResult(
                source_ref=nfo.source_ref,
                input_type=nfo.input_type,
                overall_consistency_score=0.5,
                temporal_coherence_score=0.5,
                agent_errors=["No claims to check"],
            )

        for claim in claims:
            check = await self._check_single_claim(claim)
            checks.append(check)

        # Scores globaux
        total_confidence = sum(c.confidence for c in checks)
        if total_confidence == 0:
            overall_consistency = 0.5
        else:
            overall_consistency = sum(
                (1.0 if c.is_consistent else 0.0) * c.confidence
                for c in checks
            ) / total_confidence

        # Score temporel : moyenne des absence de temporal_issues
        temporal_scores = []
        for c in checks:
            if not c.temporal_issues:
                temporal_scores.append(1.0)
            else:
                temporal_scores.append(0.0)
        temporal_coherence = sum(temporal_scores) / len(temporal_scores) if temporal_scores else 0.5

        return ContextAgentResult(
            source_ref=nfo.source_ref,
            input_type=nfo.input_type,
            overall_consistency_score=overall_consistency,
            temporal_coherence_score=temporal_coherence,
            checks=checks,
            agent_errors=errors,
        )

    async def _check_single_claim(self, claim: ExtractedClaim) -> ContextCheck:
        """Vérifie une allégation unique via la base de connaissances."""
        if self.use_mock:
            return await self._mock_check(claim)

        # Version réelle avec Wikidata
        return await self._wikidata_check(claim)

    async def _mock_check(self, claim: ExtractedClaim) -> ContextCheck:
        """Simulation pour test – à remplacer."""
        await asyncio.sleep(0.02)
        # Logique simpliste : si l'allégation contient "fusion energy" ou "ITER", on la considère cohérente
        text_lower = claim.claim_text.lower()
        if "fusion" in text_lower or "iter" in text_lower:
            is_consistent = True
            confidence = 0.85
            supporting = ["ITER est un projet de recherche sur la fusion nucléaire (source: Wikidata Q165467)."]
            contradicting = []
            temporal_issues = []
        elif "coal power plants will be fully phased out by 2025" in text_lower:
            is_consistent = False
            confidence = 0.7
            supporting = []
            contradicting = ["Selon l'AIE, le charbon fournit encore 36% de l'électricité mondiale en 2024, un abandon total avant 2030 est peu probable."]
            temporal_issues = ["L'échéance 2025 est trop proche pour une transition complète."]
        else:
            is_consistent = False
            confidence = 0.5
            supporting = []
            contradicting = ["Aucune information trouvée dans la base de connaissances."]
            temporal_issues = []
        return ContextCheck(
            claim_text=claim.claim_text,
            claim_id=claim.claim_id,
            is_consistent=is_consistent,
            confidence=confidence,
            supporting_facts=supporting,
            contradicting_facts=contradicting,
            temporal_issues=temporal_issues,
            agent_errors=[],
        )

    async def _wikidata_check(self, claim: ExtractedClaim) -> ContextCheck:
        """
        Version réelle utilisant l'API Wikidata pour rechercher des entités et
        vérifier les faits. Implémentation simplifiée – à compléter.
        """
        # 1. Extraire les entités nommées (déjà dans claim.entities)
        entities = claim.entities
        if not entities:
            # Sinon, tenter d'extraire des noms propres du texte
            import re
            entities = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', claim.claim_text)

        # 2. Requête SPARQL simplifiée via l'API de Wikidata
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Exemple : rechercher l'identifiant d'une entité
            for ent in entities[:2]:  # limite
                url = f"https://www.wikidata.org/w/api.php"
                params = {
                    "action": "wbsearchentities",
                    "search": ent,
                    "language": "en",
                    "format": "json",
                }
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("search"):
                        # Premier résultat
                        entity_id = data["search"][0]["id"]
                        # On pourrait ensuite récupérer les déclarations (claims) de l'entité
                        # pour comparer avec l'allégation.
                        pass

        # Pour l'instant, on retourne un mock (à remplacer par vraie logique)
        return await self._mock_check(claim)