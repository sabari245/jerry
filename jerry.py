"""A small library for downloading MangaDex chapters.

Example:
    from jerry import Jerry

    jerry = Jerry()
    manga = jerry.search("One Piece")[0]
    chapter = manga.chapter(1)
    path = chapter.save("./manga")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

__all__ = ["Chapter", "Jerry", "JerryError", "Manga"]


class JerryError(RuntimeError):
    """Raised when manga data cannot be retrieved or saved."""


@dataclass(frozen=True, slots=True)
class Manga:
    """A manga available through MangaDex.

    Attributes:
        mangadex_id: The MangaDex manga identifier.
        title: The MangaDex title, used when saving chapters.
    """

    mangadex_id: str
    title: str
    _jerry: Jerry = field(repr=False, compare=False)

    def chapter_count(self, language: str = "en") -> int:
        """Return the number of chapters available in a language."""
        return self._jerry._chapter_count(self, language)

    def chapter(self, number: float | str, language: str = "en") -> Chapter:
        """Fetch a numbered chapter and its page URLs."""
        return self._jerry._chapter(self, number, language)


@dataclass(frozen=True, slots=True)
class Chapter:
    """A downloadable chapter.

    Attributes:
        manga: The manga the chapter belongs to.
        id: The MangaDex chapter identifier.
        number: The chapter number requested from MangaDex.
        title: The chapter title, if supplied by MangaDex.
        pages: Direct image URLs in reading order.
    """

    manga: Manga
    id: str
    number: str
    title: str | None
    pages: tuple[str, ...]
    _jerry: Jerry = field(repr=False, compare=False)

    def save(self, directory: str | Path) -> list[Path]:
        """Download this chapter's pages and return their paths in reading order."""
        return self._jerry._save(self, directory)


class Jerry:
    """Fetch MangaDex manga and save individual chapters locally.

    Use :meth:`search` to find a manga, then use methods on the returned object.
    No third-party packages are required.
    """

    _MANGADEX_URL = "https://api.mangadex.org"
    _USER_AGENT = "jerry-python/0.1"

    def search(self, title: str, limit: int = 10) -> list[Manga]:
        """Search MangaDex by title.

        Args:
            title: The manga title to search for.
            limit: Maximum number of matches to return. Defaults to ``10``.
        """
        query = urlencode({"title": title, "limit": limit})
        matches = self._json(f"{self._MANGADEX_URL}/manga?{query}").get("data", [])
        return [Manga(str(item["id"]), self._title(item.get("attributes", {}).get("title", {})), self) for item in matches if item.get("id")]

    def _chapter_count(self, manga: Manga, language: str) -> int:
        query = urlencode({"manga": manga.mangadex_id, "translatedLanguage[]": language, "limit": 1})
        return int(self._json(f"{self._MANGADEX_URL}/chapter?{query}").get("total", 0))

    def _chapter(self, manga: Manga, number: float | str, language: str) -> Chapter:
        chapter_number = str(number)
        query = urlencode({"manga": manga.mangadex_id, "translatedLanguage[]": language, "chapter": chapter_number, "includeEmptyPages": 0})
        data = self._json(f"{self._MANGADEX_URL}/chapter?{query}").get("data", [])
        if not data:
            raise JerryError(f"Chapter {chapter_number} was not found for {manga.title}")
        attributes = data[0].get("attributes", {})
        chapter_id = data[0].get("id")
        if not chapter_id:
            raise JerryError(f"MangaDex returned an invalid chapter for {manga.title}")
        pages = self._pages(str(chapter_id))
        return Chapter(manga, str(chapter_id), chapter_number, attributes.get("title"), pages, self)

    def _save(self, chapter: Chapter, directory: str | Path) -> list[Path]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, url in enumerate(chapter.pages, 1):
            path = target / f"{index:03d}{Path(url).suffix or '.jpg'}"
            if not path.exists():
                path.write_bytes(self._bytes(url))
            paths.append(path)
        return paths

    def _pages(self, chapter_id: str) -> tuple[str, ...]:
        data = self._json(f"{self._MANGADEX_URL}/at-home/server/{chapter_id}")
        base_url, chapter = data.get("baseUrl"), data.get("chapter", {})
        image_hash, files = chapter.get("hash"), chapter.get("data", [])
        if not base_url or not image_hash or not files:
            raise JerryError("MangaDex did not provide chapter page data")
        return tuple(f"{base_url}/data/{image_hash}/{filename}" for filename in files)

    @staticmethod
    def _title(titles: dict[str, str]) -> str:
        return titles.get("en") or next(iter(titles.values()), "untitled")

    def _json(self, url: str) -> dict[str, Any]:
        try:
            return json.loads(self._bytes(url))
        except json.JSONDecodeError as error:
            raise JerryError(f"Invalid JSON returned by {url}") from error

    def _bytes(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": self._USER_AGENT})
        try:
            with urlopen(request, timeout=30) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as error:
            raise JerryError(f"Could not download {url}: {error}") from error

    @staticmethod
    def _name(value: str) -> str:
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(". ") or "untitled"
