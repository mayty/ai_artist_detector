import string
from typing import overload
from urllib.parse import unquote

from anyascii import anyascii


@overload
def unescape_name(name: str) -> str: ...


@overload
def unescape_name(name: None) -> None: ...


def unescape_name(name: str | None) -> str | None:
    if name is None:
        return name
    return unquote(name)


@overload
def normalize_name(name: str) -> str | None: ...


@overload
def normalize_name(name: None) -> None: ...


def normalize_name(name: str | None) -> str | None:
    if name is None:
        return name
    normalized = anyascii(unescape_name(name)).lower().replace('&', 'and').strip().removeprefix('the ')

    return ''.join(a for a in normalized if a not in string.punctuation and a not in string.whitespace) or None


def names_match(name_a: str, name_b: str) -> bool:
    normalized_a = normalize_name(name_a)
    normalized_b = normalize_name(name_b)

    if normalized_a is None or normalized_b is None:
        return False

    return normalized_a in normalized_b or normalized_b in normalized_a
