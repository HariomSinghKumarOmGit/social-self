# Module: browser_scraper | Purpose: Scrape social platforms via user's real browser.
# Public API: scrape_instagram_browser, scrape_twitter_browser, scrape_youtube_browser
#
# These scrapers work inside the user's REAL Chrome — no APIs, no tokens needed.
# They navigate to profiles, extract data from the page, and save to the database.

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from config import ACCOUNTS, LOOKBACK_DAYS
from database import save_post
from sessions.browser_bridge import BrowserBridge

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  INSTAGRAM — Browser-based scraper
# ──────────────────────────────────────────────────────────────

async def scrape_instagram_browser(bridge: Optional[BrowserBridge] = None) -> List[Dict[str, Any]]:
    """Scrape Instagram profiles by navigating in user's browser.

    Opens each profile page, scrolls to load posts, extracts post data
    from the DOM and __additionalDataLoaded scripts.
    """
    own_bridge = bridge is None
    if own_bridge:
        bridge = BrowserBridge()
        await bridge.connect()

    saved_items: List[Dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    try:
        for username in ACCOUNTS.get("instagram", []):
            page = None
            try:
                url = f"https://www.instagram.com/{username}/"
                page = await bridge.new_tab(url)
                await bridge.human_delay(2000, 3500)
                await bridge.scroll_down(page, times=2, delay_ms=1500)

                # Extract post data via DOM parsing
                posts = await _extract_ig_posts(page, username)

                for post in posts:
                    try:
                        post_time = post.get("timestamp")
                        if post_time and post_time < cutoff:
                            continue

                        caption = post.get("caption", "").strip() or "Instagram post"
                        likes = post.get("likes", 0)
                        comments = post.get("comments", 0)
                        engagement = likes + comments

                        post_id = save_post(
                            platform="instagram",
                            author=username,
                            content=caption,
                            post_url=post.get("url"),
                            media_url=post.get("image_url"),
                            likes=likes,
                            comments=comments,
                            shares=0,
                            saves=0,
                            views=0,
                            engagement_score=float(engagement),
                        )
                        saved_items.append({
                            "id": post_id,
                            "platform": "instagram",
                            "author": username,
                            "content": caption[:100],
                            "likes": likes,
                            "comments": comments,
                        })
                    except Exception:
                        logger.exception("Failed processing IG post for %s", username)

            except Exception:
                logger.exception("Instagram browser scrape failed for %s", username)
            finally:
                if page:
                    await bridge.close_tab(page)
                await bridge.human_delay(1500, 3000)

    finally:
        if own_bridge:
            await bridge.disconnect()

    logger.info("Instagram browser scrape done. Saved %s items.", len(saved_items))
    return saved_items


async def _extract_ig_posts(page: Page, username: str) -> List[Dict[str, Any]]:
    """Extract post data from an Instagram profile page."""
    posts = []

    try:
        # Method 1: Try extracting from __additionalDataLoaded or shared data
        raw_data = await page.evaluate("""() => {
            // Try window._sharedData (older Instagram)
            if (window._sharedData) {
                try {
                    const user = window._sharedData.entry_data.ProfilePage[0].graphql.user;
                    return JSON.stringify(user.edge_owner_to_timeline_media.edges);
                } catch(e) {}
            }
            // Try __additionalDataLoaded
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    return JSON.stringify(data);
                } catch(e) {}
            }
            return null;
        }""")

        if raw_data:
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    for edge in data[:12]:
                        node = edge.get("node", edge)
                        posts.append(_parse_ig_node(node, username))
                    if posts:
                        return posts
            except (json.JSONDecodeError, TypeError):
                pass

        # Method 2: Extract from visible post links on profile grid
        post_links = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
            return Array.from(links).slice(0, 12).map(a => ({
                url: a.href,
                img: a.querySelector('img')?.src || '',
                alt: a.querySelector('img')?.alt || ''
            }));
        }""")

        if post_links:
            for link_data in post_links:
                post_url = link_data.get("url", "")
                caption = link_data.get("alt", "Instagram post")
                image_url = link_data.get("img", "")

                posts.append({
                    "url": post_url,
                    "caption": caption,
                    "image_url": image_url,
                    "likes": 0,
                    "comments": 0,
                    "timestamp": None,
                })

        # Method 3: Visit individual posts for detailed data
        if posts and not any(p.get("likes", 0) > 0 for p in posts):
            for i, post in enumerate(posts[:6]):  # Limit to first 6
                post_url = post.get("url")
                if not post_url:
                    continue
                try:
                    detail = await _scrape_ig_post_detail(page, post_url, username)
                    if detail:
                        posts[i].update(detail)
                except Exception:
                    logger.debug("Could not get detail for %s", post_url)

    except Exception:
        logger.exception("Failed extracting IG posts for %s", username)

    return posts


async def _scrape_ig_post_detail(page: Page, post_url: str, username: str) -> Optional[Dict[str, Any]]:
    """Visit an individual IG post page to extract likes/comments."""
    try:
        await page.goto(post_url, wait_until="domcontentloaded", timeout=15_000)
        await asyncio.sleep(2)

        data = await page.evaluate(r"""() => {
            const result = {};

            // Get likes
            const likeEls = document.querySelectorAll('section span, button span');
            for (const el of likeEls) {
                const text = el.textContent || '';
                const match = text.match(/([\d,]+)\s*likes?/i);
                if (match) {
                    result.likes = parseInt(match[1].replace(/,/g, ''));
                    break;
                }
            }

            // Get caption from meta
            const meta = document.querySelector('meta[property="og:description"]');
            if (meta) {
                result.caption = meta.content;
            }

            // Get timestamp
            const time = document.querySelector('time[datetime]');
            if (time) {
                result.timestamp = time.getAttribute('datetime');
            }

            return result;
        }""")

        if data:
            result = {}
            if "likes" in data:
                result["likes"] = data["likes"]
            if "caption" in data:
                result["caption"] = data["caption"]
            if "timestamp" in data:
                try:
                    result["timestamp"] = datetime.fromisoformat(
                        data["timestamp"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass
            return result

    except Exception:
        pass
    return None


def _parse_ig_node(node: dict, username: str) -> Dict[str, Any]:
    """Parse an Instagram GraphQL node into our standard format."""
    caption = ""
    edges = node.get("edge_media_to_caption", {}).get("edges", [])
    if edges:
        caption = edges[0].get("node", {}).get("text", "")

    timestamp = None
    taken_at = node.get("taken_at_timestamp")
    if taken_at:
        try:
            timestamp = datetime.fromtimestamp(int(taken_at), tz=timezone.utc)
        except (ValueError, TypeError):
            pass

    return {
        "url": f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
        "caption": caption,
        "image_url": node.get("display_url", node.get("thumbnail_src", "")),
        "likes": node.get("edge_liked_by", {}).get("count", 0)
                 or node.get("edge_media_preview_like", {}).get("count", 0),
        "comments": node.get("edge_media_to_comment", {}).get("count", 0)
                    or node.get("edge_media_preview_comment", {}).get("count", 0),
        "timestamp": timestamp,
    }


# ──────────────────────────────────────────────────────────────
#  TWITTER/X — Browser-based scraper
# ──────────────────────────────────────────────────────────────

async def scrape_twitter_browser(bridge: Optional[BrowserBridge] = None) -> List[Dict[str, Any]]:
    """Scrape X/Twitter profiles by navigating in user's browser."""
    own_bridge = bridge is None
    if own_bridge:
        bridge = BrowserBridge()
        await bridge.connect()

    saved_items: List[Dict[str, Any]] = []

    try:
        for username in ACCOUNTS.get("twitter", []):
            page = None
            try:
                url = f"https://x.com/{username}"
                page = await bridge.new_tab(url)
                await bridge.human_delay(2500, 4000)
                await bridge.scroll_down(page, times=3, delay_ms=1500)

                tweets = await _extract_tweets(page, username)

                for tweet in tweets:
                    try:
                        content = tweet.get("text", "").strip()
                        if not content:
                            continue
                        likes = tweet.get("likes", 0)
                        comments = tweet.get("replies", 0)
                        shares = tweet.get("retweets", 0)
                        engagement = likes + comments * 3 + shares * 2

                        post_id = save_post(
                            platform="twitter",
                            author=username,
                            content=content,
                            post_url=tweet.get("url"),
                            media_url=tweet.get("image_url"),
                            likes=likes,
                            comments=comments,
                            shares=shares,
                            saves=tweet.get("bookmarks", 0),
                            views=tweet.get("views", 0),
                            engagement_score=float(engagement),
                        )
                        saved_items.append({
                            "id": post_id,
                            "platform": "twitter",
                            "author": username,
                            "content": content[:100],
                            "likes": likes,
                            "retweets": shares,
                        })
                    except Exception:
                        logger.exception("Failed processing tweet for %s", username)

            except Exception:
                logger.exception("Twitter browser scrape failed for %s", username)
            finally:
                if page:
                    await bridge.close_tab(page)
                await bridge.human_delay(1500, 3000)

    finally:
        if own_bridge:
            await bridge.disconnect()

    logger.info("Twitter browser scrape done. Saved %s items.", len(saved_items))
    return saved_items


async def _extract_tweets(page: Page, username: str) -> List[Dict[str, Any]]:
    """Extract tweet data from a Twitter/X profile page."""
    tweets = []
    try:
        raw = await page.evaluate(r"""() => {
            const articles = document.querySelectorAll('article[data-testid="tweet"]');
            return Array.from(articles).slice(0, 15).map(article => {
                const result = {};

                // Tweet text
                const textEl = article.querySelector('[data-testid="tweetText"]');
                result.text = textEl ? textEl.innerText : '';

                // Tweet URL (from timestamp link)
                const timeLink = article.querySelector('a[href*="/status/"] time');
                const linkEl = timeLink ? timeLink.closest('a') : null;
                result.url = linkEl ? 'https://x.com' + linkEl.getAttribute('href') : '';

                // Timestamp
                const timeEl = article.querySelector('time[datetime]');
                result.timestamp = timeEl ? timeEl.getAttribute('datetime') : '';

                // Engagement metrics from aria-labels on the group buttons
                const groups = article.querySelectorAll('[role="group"] button');
                groups.forEach(btn => {
                    const label = btn.getAttribute('aria-label') || '';
                    const match = label.match(/([\d,.]+[KMB]?)\s+(repl|retweet|like|bookmark|view)/i);
                    if (match) {
                        let raw = match[1].replace(/,/g, '');
                        let count = 0;
                        if (/K$/i.test(raw)) count = Math.round(parseFloat(raw) * 1000);
                        else if (/M$/i.test(raw)) count = Math.round(parseFloat(raw) * 1000000);
                        else count = parseInt(raw, 10) || 0;
                        const type = match[2].toLowerCase();
                        if (type.startsWith('repl')) result.replies = count;
                        else if (type.startsWith('retweet')) result.retweets = count;
                        else if (type.startsWith('like')) result.likes = count;
                        else if (type.startsWith('bookmark')) result.bookmarks = count;
                        else if (type.startsWith('view')) result.views = count;
                    }
                });

                // Images
                const img = article.querySelector('[data-testid="tweetPhoto"] img');
                result.image_url = img ? img.src : '';

                return result;
            });
        }""")

        if raw:
            for tweet_data in raw:
                tweets.append({
                    "text": tweet_data.get("text", ""),
                    "url": tweet_data.get("url", ""),
                    "timestamp": tweet_data.get("timestamp", ""),
                    "likes": tweet_data.get("likes", 0),
                    "replies": tweet_data.get("replies", 0),
                    "retweets": tweet_data.get("retweets", 0),
                    "bookmarks": tweet_data.get("bookmarks", 0),
                    "views": tweet_data.get("views", 0),
                    "image_url": tweet_data.get("image_url", ""),
                })

    except Exception:
        logger.exception("Failed extracting tweets for %s", username)

    return tweets


# ──────────────────────────────────────────────────────────────
#  YOUTUBE — Browser-based scraper
# ──────────────────────────────────────────────────────────────

async def scrape_youtube_browser(bridge: Optional[BrowserBridge] = None) -> List[Dict[str, Any]]:
    """Scrape YouTube channels by navigating in user's browser."""
    own_bridge = bridge is None
    if own_bridge:
        bridge = BrowserBridge()
        await bridge.connect()

    saved_items: List[Dict[str, Any]] = []

    try:
        for username in ACCOUNTS.get("youtube", []):
            page = None
            try:
                # Try both /@handle and /user/username formats
                url = f"https://www.youtube.com/@{username}/videos"
                page = await bridge.new_tab(url)
                await bridge.human_delay(2500, 4000)
                await bridge.scroll_down(page, times=2, delay_ms=1500)

                videos = await _extract_yt_videos(page, username)

                for video in videos:
                    try:
                        title = video.get("title", "").strip()
                        if not title:
                            continue
                        views = video.get("views", 0)
                        content = f"{title}\n{video.get('url', '')}"

                        post_id = save_post(
                            platform="youtube",
                            author=username,
                            content=content,
                            post_url=video.get("url"),
                            media_url=video.get("thumbnail"),
                            likes=0,
                            comments=0,
                            shares=0,
                            saves=0,
                            views=views,
                            engagement_score=float(views),
                        )
                        saved_items.append({
                            "id": post_id,
                            "platform": "youtube",
                            "author": username,
                            "content": title[:100],
                            "views": views,
                        })
                    except Exception:
                        logger.exception("Failed processing YT video for %s", username)

            except Exception:
                logger.exception("YouTube browser scrape failed for %s", username)
            finally:
                if page:
                    await bridge.close_tab(page)
                await bridge.human_delay(1500, 3000)

    finally:
        if own_bridge:
            await bridge.disconnect()

    logger.info("YouTube browser scrape done. Saved %s items.", len(saved_items))
    return saved_items


async def _extract_yt_videos(page: Page, username: str) -> List[Dict[str, Any]]:
    """Extract video data from a YouTube channel's videos tab."""
    videos = []
    try:
        raw = await page.evaluate(r"""() => {
            const renderers = document.querySelectorAll(
                'ytd-rich-item-renderer, ytd-grid-video-renderer'
            );
            return Array.from(renderers).slice(0, 12).map(r => {
                const result = {};

                // Title
                const titleEl = r.querySelector('#video-title, a#video-title-link');
                result.title = titleEl ? titleEl.textContent.trim() : '';
                result.url = titleEl ? ('https://www.youtube.com' + (titleEl.getAttribute('href') || '')) : '';

                // Thumbnail
                const thumb = r.querySelector('img');
                result.thumbnail = thumb ? thumb.src : '';

                // View count + upload time from metadata line
                const metaItems = r.querySelectorAll(
                    '#metadata-line span, .inline-metadata-item'
                );
                metaItems.forEach(span => {
                    const text = span.textContent || '';
                    const viewMatch = text.match(/([\ d,.]+[KMB]?)\s*views?/i);
                    if (viewMatch) {
                        result.viewsRaw = viewMatch[1];
                    }
                    // Check for recency (e.g., "2 days ago")
                    if (/ago|hour|day|week|month|year/i.test(text)) {
                        result.uploadedAgo = text.trim();
                    }
                });

                return result;
            });
        }""")

        if raw:
            for v in raw:
                views = _parse_yt_view_count(v.get("viewsRaw", ""))
                videos.append({
                    "title": v.get("title", ""),
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail", ""),
                    "views": views,
                    "uploaded_ago": v.get("uploadedAgo", ""),
                })

    except Exception:
        logger.exception("Failed extracting YT videos for %s", username)

    return videos


def _parse_yt_view_count(raw: str) -> int:
    """Parse YouTube view counts like '1.2M', '456K', '78,901' into int."""
    if not raw:
        return 0
    raw = raw.strip().replace(",", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if raw.upper().endswith(suffix):
            try:
                return int(float(raw[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(raw)
    except ValueError:
        return 0
