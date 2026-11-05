# -*- coding: utf-8 -*-
"""Validate translation/texts.tsv against the game's current English.

stale        the English changed since the line was translated
unknown      the key no longer exists
placeholder  {...}, %s, %d, [BUTTON] or an inline icon differ from the English
glyph        a character missing from the fonts the build uses
"""
import collections, os, re, sys
import br

FONTS = ["ubuntu", "ubuntu_m", "russian_dwarven_axe_m", "russian_dwarven_axe_l", "russian_popup"]


def glyphs():
    sets = []
    for name in FONTS:
        with open(os.path.join(br.GAME, "fonts", name + ".fnt"), encoding="utf-8", errors="replace") as f:
            sets.append({int(i) for i in re.findall(r"char id=(\d+)", f.read())})
    return set.intersection(*sets) | {10, 13}


def tokens(text):
    return collections.Counter(br.PLACEHOLDER.findall(text) + br.ICON.findall(text))


def main():
    verbose = "-v" in sys.argv
    source = {k: en for name in br.tables() for k, _, en in br.read_table(name)}
    translation = br.read_translation()
    ok_chars = glyphs()
    errors = collections.Counter()

    def report(kind, key, detail=""):
        errors[kind] += 1
        if verbose:
            print(f"{kind}: {key} {detail}")

    for key, (src, uk) in translation.items():
        if key not in source:
            report("unknown", key)
            continue
        en = source[key]
        if src != br.fingerprint(en):
            report("stale", key)
        if tokens(en) != tokens(uk):
            report("placeholder", key)
        bad = {c for c in uk if ord(c) not in ok_chars and c != br.ZERO_WIDTH and not br.ICON.match(c)}
        if bad:
            report("glyph", key, "".join(sorted(bad)))

    print(f"{len(translation)} of {len(source)} lines translated ({len(translation) * 100 // len(source)}%)")
    for kind, n in sorted(errors.items()):
        print(f"{kind}: {n}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
