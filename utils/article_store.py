"""Persistent history and freshness filtering for collected news articles."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class NoFreshArticlesError(RuntimeError):
    """Raised when a news category has no unseen article in its freshness window."""


_TRACKING_PARAMETERS = {
    "dclid",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
}


def canonicalize_url(url: str) -> str:
    """Return a stable article URL without fragments or tracking parameters."""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in _TRACKING_PARAMETERS
    ]
    query.sort()
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


class ArticleStore:
    """Mutable on-disk history of canonical article URLs by news category."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.seen: dict[str, dict[str, str]] = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            with self.path.open(encoding="utf-8") as source:
                raw = json.load(source)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

        if not isinstance(raw, dict):
            return {}

        loaded: dict[str, dict[str, str]] = {}
        for category, entries in raw.items():
            if not isinstance(category, str) or not isinstance(entries, dict):
                continue
            valid_entries = {
                url: timestamp
                for url, timestamp in entries.items()
                if isinstance(url, str) and isinstance(timestamp, str)
            }
            loaded[category] = valid_entries
        return loaded

    def has_seen(self, category: str, url: str) -> bool:
        """Return whether the canonical URL is present in the category history."""
        return canonicalize_url(url) in self.seen.get(category, {})

    def mark_seen(self, category: str, url: str, seen_at: datetime) -> None:
        """Record a canonical URL and the UTC time at which it was selected."""
        timestamp = _as_utc(seen_at).isoformat()
        self.seen.setdefault(category, {})[canonicalize_url(url)] = timestamp

    def prune(
        self,
        *,
        now: datetime | None = None,
        max_age_hours: int = 48,
    ) -> None:
        """Remove history entries older than the requested retention window."""
        current = _as_utc(now or datetime.now(timezone.utc))
        cutoff = current - timedelta(hours=max_age_hours)
        for category, entries in list(self.seen.items()):
            retained: dict[str, str] = {}
            for url, raw_timestamp in entries.items():
                try:
                    timestamp = _as_utc(datetime.fromisoformat(raw_timestamp))
                except ValueError:
                    continue
                if timestamp >= cutoff:
                    retained[url] = raw_timestamp
            if retained:
                self.seen[category] = retained
            else:
                del self.seen[category]

    def save(self) -> None:
        """Atomically persist the current history as UTF-8 JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                json.dump(self.seen, temporary, ensure_ascii=False, indent=2)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


def filter_fresh(
    articles: list[dict],
    store: ArticleStore,
    category: str,
    *,
    now: datetime | None = None,
    max_age_hours: int = 48,
) -> list[dict]:
    """Return unseen, dated articles in the freshness window, newest first."""
    current = _as_utc(now or datetime.now(timezone.utc))
    cutoff = current - timedelta(hours=max_age_hours)
    fresh: list[dict] = []
    batch_urls: set[str] = set()

    for article in articles:
        published_at = article.get("published_at")
        link = article.get("link")
        if not isinstance(published_at, datetime) or not isinstance(link, str) or not link:
            continue
        published_utc = _as_utc(published_at)
        canonical_url = canonicalize_url(link)
        if not cutoff <= published_utc <= current:
            continue
        if canonical_url in batch_urls or store.has_seen(category, canonical_url):
            continue
        batch_urls.add(canonical_url)
        fresh.append(article)

    return sorted(
        fresh,
        key=lambda article: _as_utc(article["published_at"]),
        reverse=True,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
