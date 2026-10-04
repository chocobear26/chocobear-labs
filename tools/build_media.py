#!/usr/bin/env python3
"""Prueft alle Dateien in media/ und erzeugt media/media.json fuer die Bilder-Strecke.

Laeuft in der GitHub Action vor jedem Veroeffentlichen und lokal zum Testen:
    python3 tools/build_media.py            # pruefen + media.json schreiben
    python3 tools/build_media.py --check    # nur pruefen

Bricht mit Fehler ab, sobald eine Datei gegen eine Regel verstoesst. Dann wird
die Seite NICHT veroeffentlicht. Braucht exiftool (Metadaten-Pruefung).

Dateinamen:  <app>--<titel>.<endung>      z.B.  waldlaeufer--boss-kampf.png
Breitformat: <app>--<titel>--breit.<endung>
Video-Vorschaubild (optional): gleiche Basis wie das Video, Endung .jpg/.png/.webp
Beschriftungen und Reihenfolge (optional): media/texte.json
    [{"datei": "waldlaeufer--boss-kampf.png", "text": "Der erste Boss"}]
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "media"
OUT = MEDIA / "media.json"
TEXTE = MEDIA / "texte.json"

APPS = {"mood-checker", "juntos", "waldlaeufer", "farbdorf", "lesespiel", "aemtli", "allgemein"}
BILD = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO = {".mp4", ".webm"}
MAX_BILD = 5 * 1024 * 1024
MAX_VIDEO = 40 * 1024 * 1024
NAME = re.compile(r"^([a-z-]+?)--([a-z0-9][a-z0-9-]*?)(--breit)?\.([a-z0-9]+)$")
IGNORIERT = {"media.json", "texte.json", "LIESMICH.md", ".gitkeep"}

# Metadaten, die etwas ueber Person, Ort oder Geraet verraten. Treffer = Abbruch.
VERBOTEN = re.compile(
    r"(gps|location|latitude|longitude|make$|model$|serial|lens|owner|artist|author|"
    r"creator|copyright|rights|byline|credit|contact|email|hostcomputer|cameraowner|"
    r"usercomment|imageuniqueid|devicename|software$|com\.apple\.quicktime\.(make|model|software|location))",
    re.IGNORECASE,
)
# Rein technische Gruppen, die exiftool immer liefert, werden nicht bewertet.
TECHNISCH = {"SourceFile", "ExifTool", "File", "System", "Composite"}


def fehler(liste, datei, text):
    liste.append(f"{datei}: {text}")


def metadaten(pfade):
    """Liefert {dateiname: [verdaechtige Tags]} via exiftool."""
    if not pfade:
        return {}
    if not shutil.which("exiftool"):
        sys.exit("exiftool fehlt. Ohne Metadaten-Pruefung wird nichts veroeffentlicht.")
    roh = subprocess.run(
        ["exiftool", "-j", "-G1", "-a", "-u", *map(str, pfade)],
        capture_output=True, text=True, check=False,
    )
    befund = {}
    for eintrag in json.loads(roh.stdout or "[]"):
        name = Path(eintrag["SourceFile"]).name
        treffer = []
        for schluessel, wert in eintrag.items():
            gruppe, _, tag = schluessel.partition(":")
            if not tag or gruppe in TECHNISCH or gruppe.startswith("File"):
                continue
            if VERBOTEN.search(tag) and str(wert).strip():
                treffer.append(f"{schluessel}={str(wert)[:40]}")
        befund[name] = treffer
    return befund


def main():
    nur_pruefen = "--check" in sys.argv
    probleme = []
    MEDIA.mkdir(exist_ok=True)

    dateien = sorted(p for p in MEDIA.iterdir() if p.is_file() and p.name not in IGNORIERT)
    unterordner = [p.name for p in MEDIA.iterdir() if p.is_dir()]
    for u in unterordner:
        fehler(probleme, u, "Unterordner sind nicht erlaubt, alle Dateien direkt in media/")

    eintraege = {}
    vorschau = set()
    basen = {}
    for p in dateien:
        m = NAME.match(p.name)
        ext = p.suffix.lower()
        if not m:
            fehler(probleme, p.name, "Name passt nicht zu <app>--<titel>.<endung> (nur a-z, 0-9, Bindestrich)")
            continue
        app = m.group(1)
        if app not in APPS:
            fehler(probleme, p.name, f"unbekannte App '{app}', erlaubt: {', '.join(sorted(APPS))}")
            continue
        if ext not in BILD | VIDEO:
            fehler(probleme, p.name, "Dateityp nicht erlaubt (Bilder: jpg png webp gif, Videos: mp4 webm)")
            continue
        groesse = p.stat().st_size
        if ext in BILD and groesse > MAX_BILD:
            fehler(probleme, p.name, f"Bild zu gross ({groesse // 1024} KB, max {MAX_BILD // 1024} KB)")
        if ext in VIDEO and groesse > MAX_VIDEO:
            fehler(probleme, p.name, f"Video zu gross ({groesse // 1048576} MB, max {MAX_VIDEO // 1048576} MB)")
        basis = p.name[: -len(p.suffix)]
        basen.setdefault(basis, []).append(p.name)
        eintraege[p.name] = {
            "file": p.name,
            "type": "video" if ext in VIDEO else "image",
            "app": app,
            "wide": bool(m.group(3)),
        }

    # Vorschaubilder: Bild mit gleicher Basis wie ein Video
    for basis, namen in basen.items():
        videos = [n for n in namen if eintraege[n]["type"] == "video"]
        bilder = [n for n in namen if eintraege[n]["type"] == "image"]
        if videos and bilder:
            for v in videos:
                eintraege[v]["poster"] = bilder[0]
            vorschau.update(bilder)

    for name, tags in metadaten([MEDIA / n for n in eintraege]).items():
        if tags:
            fehler(probleme, name, "enthaelt verraeterische Metadaten: " + "; ".join(tags[:6])
                   + ". Vorher mit tools/bereinigen.sh saeubern.")

    texte = []
    if TEXTE.exists():
        try:
            texte = json.loads(TEXTE.read_text(encoding="utf-8"))
            assert isinstance(texte, list)
        except Exception:
            fehler(probleme, "texte.json", "ist kein gueltiges JSON (Liste von {\"datei\", \"text\"})")
            texte = []
    reihenfolge = []
    for t in texte:
        datei = t.get("datei") if isinstance(t, dict) else None
        if datei not in eintraege:
            fehler(probleme, "texte.json", f"Datei '{datei}' gibt es nicht in media/")
            continue
        text = str(t.get("text", "")).strip()
        if len(text) > 140:
            fehler(probleme, "texte.json", f"Text zu '{datei}' ist laenger als 140 Zeichen")
        eintraege[datei]["caption"] = text
        reihenfolge.append(datei)

    if probleme:
        print("NICHT veroeffentlicht, bitte beheben:\n  - " + "\n  - ".join(probleme), file=sys.stderr)
        sys.exit(1)

    rest = sorted(n for n in eintraege if n not in reihenfolge)
    liste = [eintraege[n] for n in reihenfolge + rest if n not in vorschau]
    print(f"OK: {len(liste)} Eintraege in der Bilder-Strecke, {len(vorschau)} Vorschaubilder.")
    if not nur_pruefen:
        OUT.write_text(json.dumps(liste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
