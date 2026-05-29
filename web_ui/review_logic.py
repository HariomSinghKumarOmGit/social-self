"""Shared filtering/sorting/enrichment for review queue API."""

from __future__ import annotations

from typing import Any, Dict, List

from filters.scorer import calculate_score


def enrich_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure engagement fields and interaction score are populated."""
    row = dict(post)
    likes = int(row.get("likes") or 0)
    comments = int(row.get("comments") or 0)
    shares = int(row.get("shares") or 0)
    saves = int(row.get("saves") or 0)
    views = int(row.get("views") or 0)
    score = calculate_score(likes, comments, shares, views)
    row["engagement_score"] = score
    row["interaction_score"] = round(
        likes + comments * 3 + shares * 2 + saves * 2 + views * 0.01,
        2,
    )
    return row


def filter_and_sort_posts(
    posts: List[Dict[str, Any]],
    *,
    platform: str = "",
    author: str = "",
    query: str = "",
    sort_key: str = "interaction",
) -> List[Dict[str, Any]]:
    """Filter and sort posts for review UI."""
    filtered = [enrich_post(p) for p in posts]

    if platform == "other":
        known = {"instagram", "twitter", "youtube"}
        filtered = [p for p in filtered if str(p.get("platform", "")).lower() not in known]
    elif platform:
        filtered = [p for p in filtered if str(p.get("platform", "")).lower() == platform]

    if author:
        author_l = author.lower()
        filtered = [p for p in filtered if str(p.get("author", "")).lower() == author_l]

    if query:
        q = query.lower()
        filtered = [
            p
            for p in filtered
            if q in str(p.get("content", "")).lower()
            or q in str(p.get("author", "")).lower()
        ]

    if sort_key == "likes":
        filtered.sort(key=lambda p: int(p.get("likes") or 0), reverse=True)
    elif sort_key == "newest":
        filtered.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)
    else:
        filtered.sort(key=lambda p: float(p.get("interaction_score") or 0), reverse=True)

    return filtered


def queue_stats(posts: List[Dict[str, Any]]) -> Dict[str, int]:
    total_likes = sum(int(p.get("likes") or 0) for p in posts)
    return {"total": len(posts), "total_likes": total_likes}
