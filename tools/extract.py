# -*- coding: utf-8 -*-
"""Write local/source/strings.tsv: key, fingerprint, English, for every line."""
import os
import br


def main():
    os.makedirs(os.path.join(br.LOCAL, "source"), exist_ok=True)
    path = os.path.join(br.LOCAL, "source", "strings.tsv")
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("key\tsrc\ten\n")
        for name in br.tables():
            for key, _, en in br.read_table(name):
                f.write(f"{key}\t{br.fingerprint(en)}\t{br.esc(en)}\n")
                n += 1
    print(f"{n} lines -> {path}")


if __name__ == "__main__":
    main()
