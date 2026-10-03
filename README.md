# Nachglühen – Rezensions-Blog

Rezensionen zu Büchern, Filmen, Videospielen und Musik. Jede Seite übernimmt
automatisch das Farbschema ihres Covers – wie ein Ambilight hinter dem Fernseher.

## Neue Rezension anlegen

1. Ordner in der passenden Kategorie anlegen. Der Ordnername wird Teil der URL:

   ```
   rezensionen/
     buecher/   filme/   spiele/   musik/
       mein-titel/
         cover.jpg        ← Coverbild (jpg, png, webp …)
         rezension.md     ← Text mit Kopfbereich
         szene.jpg        ← optional: weitere Bilder für den Text
   ```

2. `rezension.md` mit Kopfbereich schreiben:

   ```markdown
   ---
   titel: Mein Titel
   von: Name der Autorin / Regie / Studio / Band
   jahr: 2024
   genre: Science-Fiction
   bewertung: 8            # Pflicht: ganze Zahl von 1 bis 10
   datum: 2026-10-03       # Veröffentlichungsdatum, bestimmt die Reihenfolge
   fazit: Ein Satz, der unter der Wertung steht.
   akzent: "#ff3399"       # optional: Akzentfarbe von Hand festlegen
   ---
   Hier beginnt der Text in Markdown. **Fett**, *kursiv*, ## Zwischenüberschriften,
   > Zitate und Bilder: ![Beschreibung](szene.jpg)
   ```

   Pflicht sind nur `titel` und `bewertung`. Ordner, deren Name mit `_`
   beginnt (z. B. `_entwurf`), werden nicht veröffentlicht.

3. Lokal ansehen:

   ```bash
   pip install -r requirements.txt
   python build.py --serve
   ```

   Dann http://localhost:8000 öffnen.

4. Committen und pushen – GitHub Actions baut und veröffentlicht die Seite.

## Wie die Farben entstehen

`build.py` analysiert jedes Cover:

- **Grundton** (Hintergrund, Text): Durchschnittsfarbe des Cover-Randes, stark abgedunkelt
- **Leuchtfarben** (Raumlicht, Akzent, Bewertungsskala): die kräftigsten Farbtöne
  des Covers – kleine, leuchtende Flächen zählen dabei mehr als große, dunkle

Hinter dem Cover liegt zusätzlich eine weichgezeichnete Kopie des Bildes, die langsam „atmet".

## Einmalig: GitHub Pages einschalten

Im Repository unter **Settings → Pages → Build and deployment → Source** „GitHub Actions" wählen.

Name und Untertitel des Blogs stehen in `config.toml`.
