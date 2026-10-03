"""Erzeugt den Rezensions-Blog als statische Website in _site/.

Aufruf:
    python build.py            # Website bauen
    python build.py --serve    # bauen und unter http://localhost:8000 anzeigen
"""

import argparse
import colorsys
import functools
import http.server
import re
import shutil
import sys
import tomllib
from datetime import date
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageOps

BASIS = Path(__file__).parent
INHALT = BASIS / "rezensionen"
AUSGABE = BASIS / "_site"

# Ordnername -> (Mehrzahl, Einzahl, Bezeichnung für "von")
KATEGORIEN = {
    "buecher": ("Bücher", "Buch", "Autor·in"),
    "filme": ("Filme", "Film", "Regie"),
    "spiele": ("Videospiele", "Videospiel", "Studio"),
    "musik": ("Musik", "Album", "Künstler·in"),
}

BILDENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


class Fehler(Exception):
    pass


# --------------------------------------------------------------------------
# Farben aus dem Cover
# --------------------------------------------------------------------------

def hls_css(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"rgb({round(r * 255)} {round(g * 255)} {round(b * 255)})"


def hex_zu_hls(wert):
    wert = wert.lstrip("#")
    r, g, b = (int(wert[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def klemmen(x, unten, oben):
    return max(unten, min(oben, x))


def farbschema(cover, akzent_override=None):
    """Liest die prägenden Farben des Covers und leitet daraus ein dunkles
    "Ambilight"-Farbschema ab: dunkler Raum, farbiges Leuchten, gut lesbarer Text."""
    with Image.open(cover) as bild:
        bild = bild.convert("RGB")
        bild.thumbnail((160, 160))
        pixel = list(bild.getdata())
        breite, hoehe = bild.size

    # Grundton des Raums: die Durchschnittsfarbe des Cover-Randes – genau
    # das, was ein Ambilight an die Wand hinter dem Fernseher wirft.
    rand = max(2, min(breite, hoehe) // 10)
    randpixel = [p for i, p in enumerate(pixel)
                 if not (rand <= i % breite < breite - rand and rand <= i // breite < hoehe - rand)]
    h0, _, s0 = colorsys.rgb_to_hls(*(sum(p[k] for p in randpixel) / len(randpixel) / 255 for k in range(3)))

    # Leuchtfarben: Farbton-Histogramm, in dem kräftige, mittelhelle Pixel
    # viel stärker zählen als dunkle oder blasse. So gewinnt die kleine pinke
    # Sonne gegen den großen dunklen Hintergrund – wie beim Hinsehen auch.
    faecher = [[0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(24)]  # Gewicht, r, g, b, Anzahl
    for r, g, b in pixel:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s < 0.25 or not 0.18 < l < 0.94:
            continue
        w = s * s * max(0.0, 1 - abs(l - 0.55) * 1.3)
        f = faecher[int(h * 24) % 24]
        f[0] += w
        f[1] += r * w
        f[2] += g * w
        f[3] += b * w
        f[4] += 1

    kandidaten = []
    for w, r, g, b, n in faecher:
        if n >= len(pixel) * 0.004:  # Einzelne Ausreißer-Pixel ignorieren
            h, l, s = colorsys.rgb_to_hls(r / w / 255, g / w / 255, b / w / 255)
            kandidaten.append({"w": w, "h": h, "l": l, "s": s})
    kandidaten.sort(key=lambda f: f["w"], reverse=True)

    leuchten = []
    if akzent_override:
        h, l, s = hex_zu_hls(akzent_override)
        leuchten.append({"h": h, "l": l, "s": s})
    for f in kandidaten:  # Bis zu drei deutlich verschiedene Farbtöne
        if all(min(abs(f["h"] - g["h"]), 1 - abs(f["h"] - g["h"])) > 0.08 for g in leuchten):
            leuchten.append(f)
        if len(leuchten) == 3:
            break
    if not leuchten:  # Schwarz-weißes oder sehr blasses Cover: neutral bleiben
        leuchten.append({"h": h0, "l": 0.6, "s": min(s0, 0.15)})
    while len(leuchten) < 3:
        leuchten.append(leuchten[-1])
    akzent = leuchten[0]

    return {
        "bg": hls_css(h0, 0.065, min(s0, 0.45)),
        "flaeche": hls_css(h0, 0.12, min(s0, 0.35)),
        "linie": hls_css(h0, 0.24, min(s0, 0.3)),
        "text": hls_css(h0, 0.93, min(s0, 0.22)),
        "gedaempft": hls_css(h0, 0.72, min(s0, 0.18)),
        "akzent": hls_css(akzent["h"], klemmen(akzent["l"], 0.62, 0.74), min(akzent["s"], 0.9)),
        "leucht1": hls_css(leuchten[0]["h"], klemmen(leuchten[0]["l"], 0.42, 0.58), min(leuchten[0]["s"] * 1.2, 1)),
        "leucht2": hls_css(leuchten[1]["h"], klemmen(leuchten[1]["l"], 0.38, 0.55), min(leuchten[1]["s"] * 1.2, 1)),
        "leucht3": hls_css(leuchten[2]["h"], klemmen(leuchten[2]["l"], 0.35, 0.5), min(leuchten[2]["s"] * 1.2, 1)),
    }


def farb_style(schema):
    return ";".join(f"--{k}:{v}" for k, v in schema.items())


# --------------------------------------------------------------------------
# Rezensionen einlesen
# --------------------------------------------------------------------------

def datum_deutsch(d):
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def lies_rezension(ordner, kategorie):
    texte = sorted(ordner.glob("*.md"))
    if not texte:
        raise Fehler(f"{ordner}: keine .md-Datei gefunden")
    roh = texte[0].read_text(encoding="utf-8")
    treffer = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", roh, re.S)
    if not treffer:
        if roh.lstrip().startswith("---"):
            raise Fehler(f"{texte[0]}: die schließende '---'-Zeile nach dem Kopfbereich fehlt")
        raise Fehler(f"{texte[0]}: Kopfbereich zwischen '---'-Zeilen fehlt")
    meta = yaml.safe_load(treffer.group(1)) or {}
    text = treffer.group(2)

    for feld in ("titel", "bewertung"):
        if feld not in meta:
            raise Fehler(f"{texte[0]}: Feld '{feld}' fehlt")
    bewertung = meta["bewertung"]
    if not isinstance(bewertung, int) or not 1 <= bewertung <= 10:
        raise Fehler(f"{texte[0]}: 'bewertung' muss eine ganze Zahl von 1 bis 10 sein")

    datum = meta.get("datum") or date.fromtimestamp(texte[0].stat().st_mtime)
    if not isinstance(datum, date):
        raise Fehler(f"{texte[0]}: 'datum' bitte als JJJJ-MM-TT angeben")

    bilder = sorted(p for p in ordner.iterdir() if p.suffix.lower() in BILDENDUNGEN)
    cover = next((p for p in bilder if p.stem.lower() == "cover"), bilder[0] if bilder else None)
    if cover is None:
        raise Fehler(f"{ordner}: kein Coverbild gefunden (z. B. cover.jpg)")

    mehrzahl, einzahl, von_label = KATEGORIEN[kategorie]
    return {
        "slug": ordner.name,
        "ordner": ordner,
        "kategorie": kategorie,
        "kategorie_name": einzahl,
        "kategorie_mehrzahl": mehrzahl,
        "von_label": von_label,
        "titel": str(meta["titel"]),
        "von": meta.get("von"),
        "jahr": meta.get("jahr"),
        "genre": meta.get("genre"),
        "fazit": meta.get("fazit"),
        "bewertung": bewertung,
        "datum": datum,
        "datum_text": datum_deutsch(datum),
        "cover": cover,
        "bilder": bilder,
        "farben": farbschema(cover, meta.get("akzent")),
        "html": markdown.markdown(text, extensions=["extra", "smarty"]),
    }


def alle_rezensionen():
    rezensionen, fehler = [], []
    for kategorie in KATEGORIEN:
        ordner = INHALT / kategorie
        if not ordner.is_dir():
            continue
        for unterordner in sorted(p for p in ordner.iterdir() if p.is_dir()):
            if unterordner.name.startswith(("_", ".")):
                continue  # z. B. _entwurf: wird nicht veröffentlicht
            try:
                rezensionen.append(lies_rezension(unterordner, kategorie))
            except Fehler as e:
                fehler.append(str(e))
    if fehler:
        print("Fehler in den Rezensionen:\n  " + "\n  ".join(fehler), file=sys.stderr)
        sys.exit(1)
    rezensionen.sort(key=lambda r: r["datum"], reverse=True)
    return rezensionen


# --------------------------------------------------------------------------
# Website schreiben
# --------------------------------------------------------------------------

def skaliere(quelle, ziel, breite):
    with Image.open(quelle) as bild:
        bild = ImageOps.exif_transpose(bild).convert("RGB")
        if bild.width > breite:
            bild = bild.resize((breite, round(bild.height * breite / bild.width)), Image.LANCZOS)
        bild.save(ziel, "JPEG", quality=86, optimize=True, progressive=True)


def bauen():
    config = tomllib.loads((BASIS / "config.toml").read_text(encoding="utf-8"))
    rezensionen = alle_rezensionen()

    if AUSGABE.exists():
        shutil.rmtree(AUSGABE)
    shutil.copytree(BASIS / "static", AUSGABE / "static")

    env = Environment(loader=FileSystemLoader(BASIS / "templates"),
                      autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)
    env.filters["farb_style"] = farb_style
    gemeinsam = {"site": config, "kategorien": KATEGORIEN}

    def schreibe(pfad, template, **daten):
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(env.get_template(template).render(**gemeinsam, **daten), encoding="utf-8")

    for i, r in enumerate(rezensionen):
        ziel = AUSGABE / r["kategorie"] / r["slug"]
        ziel.mkdir(parents=True)
        skaliere(r["cover"], ziel / "cover.jpg", 900)
        skaliere(r["cover"], ziel / "cover-klein.jpg", 480)
        for bild in r["bilder"]:
            if bild != r["cover"]:
                shutil.copy2(bild, ziel / bild.name)  # für Bilder im Rezensionstext
        schreibe(ziel / "index.html", "rezension.html", r=r, root="../../",
                 neuer=rezensionen[i - 1] if i > 0 else None,
                 aelter=rezensionen[i + 1] if i + 1 < len(rezensionen) else None)

    schreibe(AUSGABE / "index.html", "liste.html", root="", aktiv=None, rezensionen=rezensionen)
    for kategorie in KATEGORIEN:
        schreibe(AUSGABE / kategorie / "index.html", "liste.html", root="../", aktiv=kategorie,
                 rezensionen=[r for r in rezensionen if r["kategorie"] == kategorie])
    (AUSGABE / ".nojekyll").touch()
    print(f"{len(rezensionen)} Rezensionen nach {AUSGABE.relative_to(BASIS)}/ geschrieben.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="nach dem Bauen lokal anzeigen")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    bauen()
    if args.serve:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=AUSGABE)
        print(f"Vorschau: http://localhost:{args.port}  (Strg+C beendet)")
        http.server.ThreadingHTTPServer(("", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
