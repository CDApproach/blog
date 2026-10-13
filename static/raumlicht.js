// Übersicht: Filter und Raumlicht.
const raster = document.querySelector(".raster");
const filter = document.querySelector(".filter");

if (raster) {
  const karten = [...raster.querySelectorAll(".karte")];
  const FARBEN = ["--bg", "--flaeche", "--linie", "--text", "--gedaempft", "--akzent", "--leucht1", "--leucht2", "--leucht3"];
  let ruhe = karten[0];

  // Raumlicht: Die Seite übernimmt die Farben einer Karte.
  const leuchten = (karte) => {
    if (!karte) return;
    const stil = getComputedStyle(karte);
    for (const name of FARBEN) document.body.style.setProperty(name, stil.getPropertyValue(name));
  };
  for (const karte of karten) {
    karte.addEventListener("mouseenter", () => leuchten(karte));
    karte.addEventListener("focusin", () => leuchten(karte));
  }
  raster.addEventListener("mouseleave", () => leuchten(ruhe));

  if (filter) {
    const felder = [...filter.querySelectorAll("select")];
    const treffer = filter.querySelector(".treffer");
    const leer = document.querySelector(".leer-gefiltert");

    const anwenden = () => {
      const f = Object.fromEntries(felder.map((s) => [s.name, s.value]));
      let anzahl = 0;
      ruhe = null;
      for (const karte of karten) {
        const d = karte.dataset;
        const passt =
          (!f.rezensiert || d.rezensiert === f.rezensiert) &&
          (!f.dekade || d.dekade === f.dekade) &&
          (!f.bewertung || Number(d.bewertung) >= Number(f.bewertung));
        karte.hidden = !passt;
        if (passt) {
          anzahl++;
          ruhe ??= karte;
        }
      }
      treffer.textContent = `${anzahl} von ${karten.length} ${karten.length === 1 ? "Rezension" : "Rezensionen"}`;
      leer.hidden = anzahl > 0;
      leuchten(ruhe ?? karten[0]);

      // Filter in der URL merken – auch beim Wechsel der Kategorie
      const params = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
      const suche = params.toString() ? `?${params}` : "";
      history.replaceState(null, "", location.pathname + suche);
      for (const link of document.querySelectorAll(".kategorien a")) {
        link.search = suche;
      }
    };

    const start = new URLSearchParams(location.search);
    for (const s of felder) {
      if (start.has(s.name)) s.value = start.get(s.name);
      s.addEventListener("change", anwenden);
    }
    filter.addEventListener("reset", () => setTimeout(anwenden));
    filter.hidden = false;
    anwenden();
  }
}
