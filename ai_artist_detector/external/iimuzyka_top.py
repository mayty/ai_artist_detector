import html
import re
from typing import NamedTuple, TYPE_CHECKING
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
from loguru import logger
from pydantic import AnyHttpUrl

if TYPE_CHECKING:
    from cloudscraper import CloudScraper

    from ai_artist_detector.config import IimuzykaTopConfig


class PageResponse(NamedTuple):
    artists: dict[int, set[str]]
    next_page_id: int | None


class ArtistResponse(NamedTuple):
    name: str
    paths: list[tuple[str, list[tuple[str, str]]]]


class IimuzykaTopClient:
    def __init__(self, config: IimuzykaTopConfig, scraper: CloudScraper) -> None:
        self.config = config
        self.base_url = f'https://{self.config.host}'
        self._youtube_link_pattern = re.compile(r'<a[^>]*title="Youtube"[^>]*>', flags=re.IGNORECASE)
        self._href_pattern = re.compile(r'href="(?P<href>[^"]+)"')
        self._name_pattern = re.compile(r'<h1>(?P<name>.*?)</h1>')
        self._scraper = scraper

    def _get_cached_page(self, page_id: int) -> str | None:
        cache_file = self.config.cache_directory / f'page_{page_id}.html'
        if cache_file.exists():
            return cache_file.read_text(encoding='utf-8')
        return None

    def _save_cached_page(self, page_id: int, response_text: str) -> None:
        cache_file = self.config.cache_directory / f'page_{page_id}.html'
        cache_file.write_text(response_text, encoding='utf-8')

    def _save_error_page(self, page_id: int, response_text: str) -> None:
        cache_file = self.config.cache_directory / f'page_{page_id}_error.html'
        logger.warning('SavingErrorPage', page_id=page_id, error_page=cache_file)
        cache_file.write_text(response_text, encoding='utf-8')

    def _get_page_text(self, page_id: int) -> str:
        cached_response = self._get_cached_page(page_id or 0) if self.config.prioritize_cache else None

        if cached_response:
            logger.debug('UsingCachedPage', page_id=page_id)
            return cached_response

        params = {} if not page_id else {'page': page_id}
        logger.info('FetchingPage', page_id=page_id)
        response = self._scraper.get(self.base_url, params=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            self._save_error_page(page_id or 0, e.response.text)
            cached_response = self._get_cached_page(page_id or 0)
            if cached_response is None:
                raise
            logger.warning('FallingBackToCachedPage', page_id=page_id, reason=str(e))
            return cached_response

        response_text = response.text
        self._save_cached_page(page_id or 0, response_text)
        return response_text

    def get_page(self, page_id: int | None = None) -> PageResponse:
        response_text = self._get_page_text(page_id or 0)

        parser = BeautifulSoup(response_text, 'html.parser')

        artist_cards = parser.find_all('div', class_='artist-card')

        artists: dict[int, set[str]] = {}

        for card in artist_cards:
            artist_title_tag = card.find('h3', class_='artist-title')

            if artist_title_tag is None:
                logger.warning('NoArtistTitleTag', artist_card=card)
                continue

            link = artist_title_tag.find('a')

            if link is None:
                logger.warning('NoArtistLinkTag', artist_card=card)
                continue

            href = link.get('href')
            if href is None:
                logger.warning('NoArtistLinkHref', artist_card=card)
                continue

            assert isinstance(href, str)
            artist_id_str = href.strip('/')

            if not artist_id_str.isdigit():
                logger.warning('InvalidArtistId', artist_id=artist_id_str)
                continue

            artist_id = int(artist_id_str)
            tracks: set[str] = set()

            for track in card.find_all('a', class_='track-title'):
                track_name = ' '.join(track.stripped_strings)
                if track_name:
                    tracks.add(track_name)

            artists[artist_id] = tracks

        current_page_id = page_id if page_id is not None else 1
        if f'href="?page={current_page_id + 1}"' in response_text:
            next_page_id: int | None = current_page_id + 1
        else:
            next_page_id = None

        return PageResponse(artists=artists, next_page_id=next_page_id)

    def get_artist_youtube(self, artist_id: int) -> ArtistResponse:
        logger.info('FetchingArtistYoutube', artist_id=artist_id)
        response = self._scraper.get(f'{self.base_url}/{artist_id}')
        response.raise_for_status()

        name_match = self._name_pattern.search(response.text)
        name = html.unescape(name_match.group('name')) if name_match else ''

        youtube_paths: list[tuple[str, list[tuple[str, str]]]] = []
        for youtube_link_match in self._youtube_link_pattern.findall(response.text):
            href_match = self._href_pattern.search(youtube_link_match)
            if href_match is None:
                continue
            href = href_match.group('href')
            if not href:
                continue
            url = AnyHttpUrl(href)
            if (host := url.host) is None or not host.endswith('youtube.com'):
                continue

            url_path = url.path
            if url_path is None:
                continue

            url_path = unquote(url_path.strip('/'))
            if not url_path:
                continue

            youtube_paths.append((url_path, url.query_params()))

        logger.debug('FetchedArtistYoutube', artist_id=artist_id, name=name, youtube_paths=youtube_paths)

        return ArtistResponse(name=name, paths=youtube_paths)
