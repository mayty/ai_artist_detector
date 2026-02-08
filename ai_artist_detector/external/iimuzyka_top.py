import html
import re
from typing import NamedTuple, TYPE_CHECKING
from urllib.parse import unquote

import requests
from loguru import logger
from pydantic import AnyHttpUrl

if TYPE_CHECKING:
    from ai_artist_detector.config import IimuzykaTopConfig


class PageResponse(NamedTuple):
    artist_ids: set[int]
    next_page_id: int | None


class ArtistResponse(NamedTuple):
    name: str
    paths: list[tuple[str, list[tuple[str, str]]]]


class IimuzykaTopClient:
    def __init__(self, config: IimuzykaTopConfig) -> None:
        self.config = config
        self.base_url = f'https://{self.config.host}'
        self._artist_link_pattern = re.compile(r'<a[^>]*\shref="/(?P<artist_id>\d+)"')
        self._youtube_link_pattern = re.compile(r'<a[^>]*title="Youtube"[^>]*>', flags=re.IGNORECASE)
        self._href_pattern = re.compile(r'href="(?P<href>[^"]+)"')
        self._name_pattern = re.compile(r'<h1>(?P<name>.*?)</h1>')

    def get_page(self, page_id: int | None = None) -> PageResponse:
        params = {} if page_id is None else {'page': page_id}
        response = requests.get(self.base_url, params=params, timeout=self.config.timeout_seconds)
        response.raise_for_status()

        response_text = response.text

        artist_id_matches = self._artist_link_pattern.findall(response_text)

        current_page_id = page_id if page_id is not None else 1
        if f'href="?page={current_page_id + 1}"' in response_text:
            next_page_id: int | None = current_page_id + 1
        else:
            next_page_id = None

        return PageResponse(artist_ids=set(map(int, artist_id_matches)), next_page_id=next_page_id)

    def get_artist_youtube(self, artist_id: int) -> ArtistResponse:
        logger.info('FetchingArtistYoutube', artist_id=artist_id)
        response = requests.get(f'{self.base_url}/{artist_id}', timeout=self.config.timeout_seconds)
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
