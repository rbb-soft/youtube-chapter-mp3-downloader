from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TRCK, TPE1, TALB, TDRC


def tag_mp3(
    path: Path,
    track_number: int,
    title: str,
    artist: str,
    album: str,
    year: str,
) -> None:
    """Write ID3v2.4 tags to an MP3 file, replacing any existing tags."""
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("TIT2")
    tags.delall("TRCK")
    tags.delall("TPE1")
    tags.delall("TALB")
    tags.delall("TDRC")

    tags.add(TIT2(encoding=3, text=title))
    tags.add(TRCK(encoding=3, text=str(track_number)))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(TALB(encoding=3, text=album))
    tags.add(TDRC(encoding=3, text=year))

    tags.save(path, v2_version=4)
