# -*- coding: utf-8 -*-
"""Glossary candidates with the official Darkest Dungeon translations beside them.

    py tools/terms.py

Writes local/terms.csv: category, key, en, freq (Black Reliquary lines that use
the term), dd1_ru (Darkest Dungeon, installed), dd2_uk and dd2_ru (Darkest
Dungeon II, from DD2Localization/). Game text, so it stays in local/.
"""
import collections, csv, glob, os, re, struct
import br

DD1 = os.path.join(os.path.dirname(br.GAME), "DarkestDungeon", "localization")
DD2 = os.path.join(br.ROOT, "DD2Localization", "Poedit")
OUT = os.path.join(br.LOCAL, "terms.csv")

# key prefix -> category; the first match wins, so specific prefixes go first
FAMILIES = [
    ("hero_class_name", "герой"),
    ("enemy_type_name", "фракція"),
    ("str_affliction_name", "вада"),
    ("str_virtue_name", "чеснота"),
    ("str_glossary_term", "термін"),
    ("dungeon_name", "місце"),
    ("town_name", "місце"),
    ("town_quest_name", "завдання"),
    ("upgrade_tree_name", "покращення"),
    ("str_inventory_title_supply", "предмет"),
    ("str_inventory_title_estate", "предмет"),
    ("trinket_rarity", "рідкість"),
    ("str_quirk_name", "риса"),
    ("combat_skill_name", "навичка"),
    ("camping_skill_name", "табір"),
    ("str_monstername", "монстр"),
]
SKIP = {"additional information", "unused", "if you see this something is wrong", ""}
TAGGED = re.compile(r"\{colour_start\|[^}]*\}([^{}]+?)\{colour_end\}")


def clean(text):
    text = re.sub(r"<[^>]+>|\{[^{}]*\}|\[[^\]]*\]", "", text.replace(br.ZERO_WIDTH, ""))
    return re.sub(r"\s+", " ", text).strip(" :!.,\"'")


def read_loc2(path):
    """Red Hook's .loc2: key hash -> [variants]."""
    with open(path, "rb") as f:
        b = f.read()
    a, d, strings = struct.unpack_from("<3I", b, 0)
    out = {}
    for i in range(512):
        off, n = struct.unpack_from("<2I", b, 12 + 8 * i)
        if not 0x100c <= off < a:
            continue
        for j in range(n):
            h, idx, _ = struct.unpack_from("<3I", b, off + 12 * j)
            start, count = struct.unpack_from("<2I", b, a + 8 * idx)
            texts = []
            for k in range(start, start + count):
                so, sl, _ = struct.unpack_from("<3I", b, d + 12 * k)
                texts.append(b[strings + so:strings + so + sl - 1].decode("utf-8", "replace"))
            out[h] = texts
    return out


def dd1_index():
    en, ru = read_loc2(os.path.join(DD1, "english.loc2")), read_loc2(os.path.join(DD1, "russian.loc2"))
    index = collections.defaultdict(collections.Counter)
    for h, texts in en.items():
        if h in ru and len(texts) == len(ru[h]):
            for e, r in zip(texts, ru[h]):
                index[clean(e).lower()][clean(r)] += 1
    return index


def read_po(path):
    """-> {msgctxt: (msgid, msgstr, fuzzy)}"""
    out, entry, field, fuzzy = {}, {}, None, False

    def flush():
        nonlocal entry, fuzzy
        if "msgid" in entry and entry["msgid"]:
            out[entry.get("msgctxt", entry["msgid"])] = (entry["msgid"], entry.get("msgstr", ""), fuzzy)
        entry, fuzzy = {}, False

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                flush()
            elif line.startswith("#,") and "fuzzy" in line:
                fuzzy = True
            elif line.startswith("#"):
                continue
            elif line.startswith(("msgctxt ", "msgid ", "msgstr ")):
                field, value = line.split(" ", 1)
                if field == "msgctxt" and "msgid" in entry:
                    flush()
                entry[field] = value[1:-1]
            elif line.startswith('"') and field:
                entry[field] += line[1:-1]
    flush()
    return out


def dd2_index():
    index = collections.defaultdict(lambda: (collections.Counter(), collections.Counter()))
    for uk_path in glob.glob(os.path.join(DD2, "**", "uk.po"), recursive=True):
        uk, ru = read_po(uk_path), read_po(os.path.join(os.path.dirname(uk_path), "ru.po"))
        for ctxt, (en, text, fuzzy) in uk.items():
            unesc = lambda s: s.replace('\\"', '"').replace("\\n", " ")
            key = clean(unesc(en)).lower()
            if text:
                index[key][0][clean(unesc(text)) + (" (fuzzy)" if fuzzy else "")] += 1
            if ctxt in ru and ru[ctxt][1]:
                index[key][1][clean(unesc(ru[ctxt][1]))] += 1
    return index


def variants(counter):
    return " | ".join(t for t, _ in counter.most_common(3))


def main():
    rows = [(k, en) for name in br.tables() for k, _, en in br.read_table(name)]
    terms = {}
    for key, en in rows:
        family = key.split("/", 1)[1]
        for prefix, category in FAMILIES:
            if family.startswith(prefix):
                term = clean(en)
                if term.lower() not in SKIP and len(term) <= 40 and term.lower() not in terms:
                    terms[term.lower()] = (category, key, term)
                break
    for key, en in rows:
        for m in TAGGED.finditer(en):
            term = clean(m.group(1))
            if 2 < len(term) <= 30 and re.match(r"[A-Za-z]", term) and term.lower() not in terms:
                terms[term.lower()] = ("ключове слово", key, term)

    texts = [clean(en).lower() for _, en in rows]
    blob = "\n".join(texts)
    dd1, dd2 = dd1_index(), dd2_index()
    out = []
    for low, (category, key, term) in terms.items():
        freq = len(re.findall(r"(?<![a-z])" + re.escape(low) + r"(?![a-z])", blob))
        uk, ru = dd2.get(low, (collections.Counter(), collections.Counter()))
        out.append([category, key, term, freq, variants(dd1.get(low, collections.Counter())), variants(uk), variants(ru)])
    out = [r for r in out if r[3] >= 2 or r[0] not in ("ключове слово",)]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "key", "en", "freq", "dd1_ru", "dd2_uk", "dd2_ru"])
        w.writerows(out)
    found = collections.Counter(r[0] for r in out if r[5])
    print(f"{len(out)} terms -> {OUT}")
    for category, n in collections.Counter(r[0] for r in out).most_common():
        print(f"  {category:15} {n:4}  with DD2 uk: {found[category]}")


if __name__ == "__main__":
    main()
