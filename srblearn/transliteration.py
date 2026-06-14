"""Транслитерация сербского: кириллица → латиница."""

from __future__ import annotations

_MULTI_REPLACEMENTS = (
    ("Џ", "Dž"),
    ("џ", "dž"),
    ("Љ", "Lj"),
    ("љ", "lj"),
    ("Њ", "Nj"),
    ("њ", "nj"),
)

_SINGLE_REPLACEMENTS = {
    "А": "A",
    "а": "a",
    "Б": "B",
    "б": "b",
    "В": "V",
    "в": "v",
    "Г": "G",
    "г": "g",
    "Д": "D",
    "д": "d",
    "Ђ": "Đ",
    "ђ": "đ",
    "Е": "E",
    "е": "e",
    "Ж": "Ž",
    "ж": "ž",
    "З": "Z",
    "з": "z",
    "И": "I",
    "и": "i",
    "Ј": "J",
    "ј": "j",
    "К": "K",
    "к": "k",
    "Л": "L",
    "л": "l",
    "М": "M",
    "м": "m",
    "Н": "N",
    "н": "n",
    "О": "O",
    "о": "o",
    "П": "P",
    "п": "p",
    "Р": "R",
    "р": "r",
    "С": "S",
    "с": "s",
    "Т": "T",
    "т": "t",
    "Ћ": "Ć",
    "ћ": "ć",
    "У": "U",
    "у": "u",
    "Ф": "F",
    "ф": "f",
    "Х": "H",
    "х": "h",
    "Ц": "C",
    "ц": "c",
    "Ч": "Č",
    "ч": "č",
    "Ш": "Š",
    "ш": "š",
}


def cyrillic_to_latin(text: str) -> str:
    result = text
    for src, dst in _MULTI_REPLACEMENTS:
        result = result.replace(src, dst)
    return "".join(_SINGLE_REPLACEMENTS.get(char, char) for char in result)
