# -*- coding: utf-8 -*-
"""Build the Ukrainian language files from translation/ and the installed game.

    py tools/build.py               build into local/build/
    py tools/build.py --install     build and copy into the game
    py tools/build.py --proofread   ship proofread lines only (for releases)
    py tools/build.py --uninstall   remove everything the install added

Lines without a current translation stay English.
"""
import os, re, shutil, subprocess, sys
import br

BUILD = os.path.join(br.LOCAL, "build")
FONTS = [
    ("dwarven_axe_medium", "russian_dwarven_axe_m", "ukrainian_dwarven_axe_m"),
    ("dwarven_axe_large", "russian_dwarven_axe_l", "ukrainian_dwarven_axe_l"),
    ("popup", "russian_popup", "ukrainian_popup"),
]
LOC_FILES = [f"{br.LANG}.loc2", os.path.join("pc", f"{br.LANG}.loc2")]
OVERRIDE = re.compile(r'font_language_override: \.language "' + br.LANG + r'".*\n')


def table_with_language(name, translation):
    with open(os.path.join(br.GAME, "localization", name), encoding="utf-8-sig") as f:
        text = f.read()
    lines = []
    for key, id_, en in br.read_table(name):
        src, uk = translation.get(key, (None, None))
        body = uk if src == br.fingerprint(en) else en
        if id_ == br.LABEL_ID:
            body = br.LABEL
        lines.append(f'<entry id="{id_}"><![CDATA[{body}]]></entry>')
    block = f'<language id="{br.LANG}">\n' + "\n".join(lines) + "\n</language>\n"
    return text.replace("</root>", block + "</root>")


def build_strings():
    work = os.path.join(BUILD, "tree")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "_windows"))
    shutil.copytree(os.path.join(br.GAME, "localization"), os.path.join(work, "localization"))
    win = os.path.join(br.GAME, "_windows")
    for name in os.listdir(win):
        if name == "localization.exe" or name.endswith(".dll"):
            shutil.copy(os.path.join(win, name), os.path.join(work, "_windows"))
    translation = br.read_translation()
    if "--proofread" in sys.argv:
        import proof
        keys = proof.proofread_keys()
        translation = {k: v for k, v in translation.items() if k in keys}
    for name in br.tables():
        with open(os.path.join(work, "localization", name), "w", encoding="utf-8") as f:
            f.write(table_with_language(name, translation))
    # localization.exe never exits on its own once it has written the files.
    loc = os.path.join(work, "localization")
    with open(os.path.join(BUILD, "localization.log"), "wb") as log:
        proc = subprocess.Popen([os.path.join(work, "_windows", "localization.exe")], cwd=loc,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            proc.wait(150)
        except subprocess.TimeoutExpired:
            proc.kill()
    for rel in LOC_FILES:
        target = os.path.join(BUILD, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(os.path.join(loc, rel), target)


def build_fonts():
    out = os.path.join(BUILD, "fonts")
    os.makedirs(out, exist_ok=True)
    fonts = os.path.join(br.GAME, "fonts")
    for _, src, dst in FONTS:
        with open(os.path.join(fonts, src + ".fnt"), encoding="utf-8", errors="surrogateescape", newline="") as f:
            text = f.read()
        with open(os.path.join(out, dst + ".fnt"), "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(text.replace(src, dst))
        shutil.copy(os.path.join(fonts, src + "_0.tga"), os.path.join(out, dst + "_0.tga"))


def read_config():
    with open(os.path.join(br.GAME, "fonts", "fonts.darkest"), encoding="utf-8", newline="") as f:
        return OVERRIDE.sub("", f.read())


def write_config(text):
    with open(os.path.join(br.GAME, "fonts", "fonts.darkest"), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def install():
    for rel in LOC_FILES:
        shutil.copy(os.path.join(BUILD, rel), os.path.join(br.GAME, "localization", rel))
    for name in os.listdir(os.path.join(BUILD, "fonts")):
        shutil.copy(os.path.join(BUILD, "fonts", name), os.path.join(br.GAME, "fonts", name))
    add = "".join(f'font_language_override: .language "{br.LANG}" .font "{font}" '
                  f'.file "fonts/{dst}.fnt" .point_sample false\n' for font, _, dst in FONTS)
    text = read_config()
    at = text.index("font_language_override")
    write_config(text[:at] + add + text[at:])


def uninstall():
    write_config(read_config())
    for rel in LOC_FILES:
        path = os.path.join(br.GAME, "localization", rel)
        if os.path.exists(path):
            os.remove(path)
    for _, _, dst in FONTS:
        for suffix in (".fnt", "_0.tga"):
            path = os.path.join(br.GAME, "fonts", dst + suffix)
            if os.path.exists(path):
                os.remove(path)


def main():
    if "--uninstall" in sys.argv:
        uninstall()
        return
    os.makedirs(BUILD, exist_ok=True)
    build_strings()
    build_fonts()
    if "--install" in sys.argv:
        install()
    print("done")


if __name__ == "__main__":
    main()
