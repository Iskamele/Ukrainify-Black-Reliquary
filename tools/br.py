# -*- coding: utf-8 -*-
"""Shared plumbing: the game's string tables and the translation file.

A string table holds <entry id> leaves under <language id="english">. An id may
repeat (bark variants), so a line's key is "<table>/<id>#<n>", n counting the
repeats inside that table.
"""
import hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.environ.get("BR_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Black Reliquary")
LOCAL = os.path.join(ROOT, "local")
TRANSLATION = os.path.join(ROOT, "translation", "texts.tsv")

# The executable's language list is fixed; Ukrainian occupies this slot.
LANG = "french"
LABEL_ID = "str_language_" + LANG
LABEL = "українська"

ENTRY = re.compile(r'<entry id="([^"]+)"[^>]*>(.*?)</entry>', re.S)
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%[-+]?\d*[sd]|\[[A-Z][A-Z ]*\]")

# Inline icons are drawn as IPA letters, and tooltips are padded with zero-width spaces.
ICON = re.compile("[ɐ-˿]")
ZERO_WIDTH = "​"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def tables():
    folder = os.path.join(GAME, "localization")
    return sorted(n for n in os.listdir(folder) if n.endswith(".string_table.xml"))


def read_table(name):
    with open(os.path.join(GAME, "localization", name), encoding="utf-8-sig") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    english = re.search(r'<language id="english">(.*?)</language>', text, re.S).group(1)
    table, seen, out = name.split(".")[0], {}, []
    for id_, raw in ENTRY.findall(english):
        raw = raw.strip()
        if raw.startswith("<![CDATA[") and raw.endswith("]]>"):
            raw = raw[9:-3]
        n = seen.get(id_, 0)
        seen[id_] = n + 1
        out.append((f"{table}/{id_}#{n}", id_, raw))
    return out


def fingerprint(en):
    return hashlib.sha1(en.encode("utf-8")).hexdigest()[:8]


def esc(s):
    return s.replace("\\", "\\\\").replace("\r", "").replace("\t", "\\t").replace("\n", "\\n")


def unesc(s):
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)


def read_translation():
    """key -> (fingerprint of the English it came from, Ukrainian)"""
    if not os.path.exists(TRANSLATION):
        return {}
    out = {}
    with open(TRANSLATION, encoding="utf-8") as f:
        next(f, None)
        for line in f:
            key, src, uk = line.rstrip("\n").split("\t", 2)
            out[key] = (src, unesc(uk))
    return out


def write_translation(lines):
    with open(TRANSLATION, "w", encoding="utf-8", newline="\n") as f:
        f.write("key\tsrc\tuk\n")
        for key in sorted(lines):
            src, uk = lines[key]
            f.write(f"{key}\t{src}\t{esc(uk)}\n")
