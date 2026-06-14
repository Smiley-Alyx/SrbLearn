"""Тесты transliteration."""

from srblearn.transliteration import cyrillic_to_latin


def test_cyrillic_to_latin_basic() -> None:
    assert cyrillic_to_latin("здраво") == "zdravo"
    assert cyrillic_to_latin("хвала") == "hvala"
    assert cyrillic_to_latin("ћутање") == "ćutanje"
    assert cyrillic_to_latin("ђак") == "đak"
    assert cyrillic_to_latin("човек") == "čovek"
    assert cyrillic_to_latin("љубав") == "ljubav"
    assert cyrillic_to_latin("њива") == "njiva"
    assert cyrillic_to_latin("џем") == "džem"
