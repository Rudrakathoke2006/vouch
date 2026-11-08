import uuid
from typing import Dict, Any, List, Optional
import imagehash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from api.src.models import Fingerprint, Campaign


async def check_invoice_reuse(
    session: AsyncSession,
    invoice_number: str,
    payee_id: str,
    total: float,
    current_campaign_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """
    Checks if identical invoice fingerprint appeared in another campaign (H5 check).
    Fingerprint format: {invoice_number}:{payee_id}:{total:.2f}
    """
    fingerprint_val = f"{invoice_number.strip().upper()}:{payee_id.strip().upper()}:{total:.2f}"
    
    stmt = (
        select(Fingerprint)
        .where(Fingerprint.kind == "invoice")
        .where(Fingerprint.value == fingerprint_val)
        .where(Fingerprint.campaign_id != current_campaign_id)
    )
    result = await session.execute(stmt)
    existing = result.scalars().first()


    if existing:
        return {
            "duplicate": True,
            "fingerprint": fingerprint_val,
            "conflict_campaign_id": str(existing.campaign_id),
            "conflict_evidence_id": str(existing.evidence_id) if existing.evidence_id else None,
        }
    return None


async def check_image_phash_reuse(
    session: AsyncSession,
    phash_str: Optional[str],
    current_campaign_id: uuid.UUID,
    threshold: int = 6,
) -> Optional[Dict[str, Any]]:
    """
    Checks if perceptual image hash is near-duplicate of another campaign's image (S2 soft signal).
    Hamming distance <= 6 indicates near-identical visual content.
    """
    if not phash_str:
        return None

    try:
        target_hash = imagehash.hex_to_hash(phash_str)
    except Exception:
        return None

    stmt = (
        select(Fingerprint)
        .where(Fingerprint.kind == "image")
        .where(Fingerprint.campaign_id != current_campaign_id)
    )
    result = await session.execute(stmt)
    fingerprints = result.scalars().all()

    closest_match = None
    min_dist = 999

    for fp in fingerprints:
        try:
            other_hash = imagehash.hex_to_hash(fp.value)
            dist = int(target_hash - other_hash)
            if dist < min_dist:
                min_dist = dist
                closest_match = fp
        except Exception:
            continue

    if closest_match and min_dist <= threshold:
        return {
            "reused": True,
            "distance": int(min_dist),
            "conflict_campaign_id": str(closest_match.campaign_id),
            "conflict_evidence_id": str(closest_match.evidence_id) if closest_match.evidence_id else None,
        }

    return None


async def check_story_text_reuse(
    session: AsyncSession,
    story_text: str,
    current_campaign_id: uuid.UUID,
    threshold: float = 0.85,
) -> Optional[Dict[str, Any]]:
    """
    Checks if campaign story text is a near-duplicate of another campaign using TF-IDF (S3 soft signal).
    Cosine similarity >= 0.85 indicates copied or near-duplicate story text.
    """
    if not story_text or len(story_text.strip()) < 30:
        return None

    stmt = select(Campaign).where(Campaign.id != current_campaign_id)
    result = await session.execute(stmt)
    other_campaigns = result.scalars().all()

    if not other_campaigns:
        return None

    corpus = [c.story for c in other_campaigns]
    campaign_ids = [str(c.id) for c in other_campaigns]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(corpus + [story_text])
        cosine_sims = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]

        max_idx = cosine_sims.argmax()
        max_score = float(cosine_sims[max_idx])

        if max_score >= threshold:
            return {
                "reused": True,
                "similarity": round(max_score, 4),
                "conflict_campaign_id": campaign_ids[max_idx],
            }
    except Exception:
        pass

    return None
