import re

_INVALID = re.compile(r'[\\/*?:"><|]')
_MAX_LEN = 200
_MAX_ALBUM_DIR_LEN = 120


def sanitize_filename(name: str) -> str:
    """Replace filesystem-unsafe characters and trim length.

    Keeps unicode letters/digits/punctuation intact (so non-ASCII titles
    survive), only strips the characters that would break on Win/Mac/Linux.
    """
    name = (name or "").strip()
    name = _INVALID.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = "untitled"
    return name[:_MAX_LEN]


def strip_artist_prefix(title: str, artist: str) -> str:
    """If title starts with '<artist> - ' (case-insensitive), drop it.

    YouTube uploads often follow the pattern "Artist - Album Title". When
    we already use the uploader as the artist, including it in the title
    produces duplication like "Artist - Artist - Album".
    """
    if not artist or not title:
        return title
    artist_norm = artist.lower().strip()
    title_norm = title.lower().lstrip()
    if not title_norm.startswith(artist_norm):
        return title
    rest = title[len(artist):].lstrip(" -–—:|·")
    return rest if rest and rest != title else title


def derive_album_dir(artist: str, album: str, year: str | None) -> str:
    safe_artist = sanitize_filename(artist)
    safe_album = sanitize_filename(strip_artist_prefix(album, artist))
    suffix = f" ({year})" if year else ""
    full = f"{safe_artist} - {safe_album}{suffix}"
    if len(full) <= _MAX_ALBUM_DIR_LEN:
        return full
    available = _MAX_ALBUM_DIR_LEN - len(safe_artist) - 3 - len(suffix)
    if available < 10:
        available = 10
    return f"{safe_artist} - {safe_album[:available]}{suffix}"
