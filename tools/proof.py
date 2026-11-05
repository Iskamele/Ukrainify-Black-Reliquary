# -*- coding: utf-8 -*-
"""Manual proofreading of the glossary and the translation in one CSV.

translation/proofreading.csv (UTF-8 with BOM, ";"-separated, for Excel):

  ключ       the row's key (leave it alone); glossary rows start with "glossary:"
  розділ     where the row belongs, to filter by
  EN         the original
  UA         the translation: edit it in place
  вичитано   ✓ once checked; ✗ or anything else flags it for a fix
  дата       filled in by the tool: the day the row was marked
  коментар   free notes; a glossary row starts with its alternatives
  відбиток   filled in by the tool: what the row said when it was written out

Running the tool syncs both ways: an edited UA goes to translation/texts.tsv or
translation/glossary.csv, and the CSV is written again. A mark is dropped when
the text changed after it was set. A checked glossary row becomes approved.

    py tools/proof.py            sync
    py tools/proof.py --status   progress by section
    py tools/proof.py --web      sync, then proofread in the browser:
                                 → accept, ← reject, ↓ comment, ↑ back
"""
import collections, csv, datetime, io, json, os, re, sys
import br

FOLDER = os.path.dirname(br.TRANSLATION)
PATH = os.path.join(FOLDER, "proofreading.csv")
GLOSSARY = os.path.join(FOLDER, "glossary.csv")
GLOSSARY_HEAD = ["EN", "UA", "альтернатива", "категорія", "примітка", "затверджено"]
HEAD = ["ключ", "розділ", "EN", "UA", "вичитано", "дата", "коментар", "відбиток"]
OK_MARKS = {"✓", "✔", "+", "v", "V", "1"}
EXCEL_ERROR = re.compile(r"^#(NAME\?|ИМЯ\?|ІМ'Я\?|VALUE!|ЗНАЧ!|REF!|ССЫЛКА!|ПОСИЛАННЯ!|N/A|Н/Д)")


def ok(mark):
    return mark.strip() in OK_MARKS


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(path, head, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(head)
    for r in rows:
        w.writerow([r[h] for h in head])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        f.write(buf.getvalue())
    os.replace(tmp, path)


def read_sheet():
    if not os.path.isfile(PATH):
        return {}
    out = {}
    for r in read_csv(PATH):
        r["EN"], r["UA"] = br.unesc(r["EN"]), br.unesc(r["UA"])
        out[r["ключ"]] = r
    return out


def write_sheet(rows):
    write_csv(PATH, HEAD, [{**r, "EN": br.esc(r["EN"]), "UA": br.esc(r["UA"])} for r in rows])


def glossary_note(g):
    parts = [g["примітка"].strip()]
    if g["альтернатива"].strip():
        parts.insert(0, "або: " + g["альтернатива"].strip())
    if g["затверджено"].startswith("рішення"):
        parts.insert(0, "рішення потрібне")
    return ". ".join(p for p in parts if p)


def sync():
    sheet = read_sheet()
    source = {k: en for name in br.tables() for k, _, en in br.read_table(name)}
    translation = br.read_translation()
    glossary = read_csv(GLOSSARY)
    by_en = {"glossary:" + g["EN"]: g for g in glossary}
    today = datetime.date.today().isoformat()
    marks, edited, dropped, skipped = {}, 0, [], []

    def current(key):
        return by_en[key]["UA"] if key in by_en else translation[key][1]

    for key, r in sheet.items():
        if key not in by_en and key not in translation:
            skipped.append(key)
            continue
        if EXCEL_ERROR.match(r["UA"]):
            skipped.append(key)
            continue
        user_changed = br.fingerprint(r["UA"]) != r["відбиток"]
        cur = current(key)
        if user_changed and r["UA"] != cur:
            edited += 1
            if key in by_en:
                by_en[key]["UA"] = r["UA"]
            else:
                translation[key] = (translation[key][0], r["UA"])
        if ok(r["вичитано"]) and not user_changed and br.fingerprint(cur) != r["відбиток"]:
            dropped.append(key)
            continue
        marks[key] = r

    for key, g in by_en.items():
        r = marks.get(key)
        if r and ok(r["вичитано"]):
            g["затверджено"] = "✓"
        elif g["затверджено"] == "✓":
            g["затверджено"] = ""

    rows = []

    def add(key, part, en, ua, note):
        r = marks.get(key, {})
        mark = r.get("вичитано", "").strip()
        rows.append({"ключ": key, "розділ": part, "EN": en, "UA": ua,
                     "вичитано": "✓" if ok(mark) else mark,
                     "дата": (r.get("дата") or today) if ok(mark) else "",
                     "коментар": r.get("коментар", note), "відбиток": br.fingerprint(ua)})

    for g in glossary:
        add("glossary:" + g["EN"], "глосарій/" + g["категорія"], g["EN"], g["UA"], glossary_note(g))
    for key, en in source.items():
        if key in translation:
            add(key, key.split("/")[0], en.replace(br.ZERO_WIDTH, ""), translation[key][1], "")

    br.write_translation(translation)
    write_csv(GLOSSARY, GLOSSARY_HEAD, glossary)
    write_sheet(rows)
    print(f"{len(rows)} rows, {edited} edited, {len(dropped)} marks dropped, {len(skipped)} skipped")
    for key in skipped:
        print("skipped", key)


def proofread_keys():
    translation = br.read_translation()
    return {k for k, r in read_sheet().items()
            if ok(r["вичитано"]) and k in translation and br.fingerprint(translation[k][1]) == r["відбиток"]}


def status():
    sheet = read_sheet()
    total, done = collections.Counter(), collections.Counter()
    for r in sheet.values():
        total[r["розділ"]] += 1
        done[r["розділ"]] += ok(r["вичитано"])
    print(f"proofread {sum(done.values())} of {sum(total.values())} rows")
    for part in sorted(total):
        print(f"  {part:28} {done[part]:5} / {total[part]:5}")
    for k, r in sheet.items():
        if r["вичитано"].strip() and not ok(r["вичитано"]):
            print(f"  flagged {k}: {r['коментар']}")


def set_mark(key, mark, note):
    sheet = read_sheet()
    r = sheet[key]
    if not (ok(mark) and ok(r["вичитано"])):
        r["дата"] = datetime.date.today().isoformat() if ok(mark) else ""
    r["вичитано"], r["коментар"] = mark, note
    write_sheet(sheet.values())


def web(port=8723):
    import http.server, webbrowser
    sync()
    page = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof.html")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body, ctype="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                with open(page, "rb") as f:
                    self.reply(200, f.read(), "text/html; charset=utf-8")
            elif self.path == "/rows":
                self.reply(200, [{"key": k, "section": r["розділ"], "en": r["EN"], "ua": r["UA"], "forms": "",
                                  "mark": r["вичитано"], "note": r["коментар"]} for k, r in read_sheet().items()])
            elif self.path == "/names":
                self.reply(200, {})
            else:
                self.reply(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/mark":
                return self.reply(404, {"error": "not found"})
            try:
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                set_mark(req["key"], req["mark"], req["note"])
            except PermissionError:
                return self.reply(423, {"error": "proofreading.csv зайнятий іншою програмою (Excel?). Закрийте його."})
            except KeyError as e:
                return self.reply(409, {"error": f"рядка {e} немає в CSV"})
            self.reply(200, {"ok": True})

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"proofreading at {url}  (Ctrl+C stops it)")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    server.serve_forever()


def main():
    if "--status" in sys.argv:
        status()
    elif "--web" in sys.argv:
        web()
    else:
        sync()


if __name__ == "__main__":
    main()
