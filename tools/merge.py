# -*- coding: utf-8 -*-
"""Merge a batch into translation/texts.tsv.

    py tools/merge.py <batch.tsv>

A batch is UTF-8 text, one "key<TAB>Ukrainian" per line, with \\n and \\t escapes.
"""
import re, sys
import br


def main():
    source = {k: en for name in br.tables() for k, _, en in br.read_table(name)}
    lines = {k: (src, br.esc(uk)) for k, (src, uk) in br.read_translation().items()}
    added = 0
    with open(sys.argv[1], encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            key, uk = line.split("\t", 1)
            if key not in source:
                sys.exit(f"line {number}: unknown key {key}")
            en = source[key]
            # Tooltip layout relies on the zero-width padding at the end of a line.
            pad = re.search(br.ZERO_WIDTH + "+$", en)
            lines[key] = (br.fingerprint(en), uk + (pad.group() if pad else ""))
            added += 1
    with open(br.TRANSLATION, "w", encoding="utf-8", newline="\n") as f:
        f.write("key\tsrc\tuk\n")
        for key in sorted(lines):
            f.write(f"{key}\t{lines[key][0]}\t{lines[key][1]}\n")
    print(f"{added} lines merged, {len(lines)} in total")


if __name__ == "__main__":
    main()
