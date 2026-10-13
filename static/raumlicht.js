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
    const felder = [...filter.querySelectorAll("select, input")];
    // Klein, ohne Akzente: „andric“ findet „Andrić“, „mueller“ bleibt aber „mueller“
    const normal = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    for (const karte of karten) karte.dataset.suche = normal(karte.dataset.suche || "");
    const treffer = filter.querySelector(".treffer");
    // Für die Sortierung ohne führenden Artikel: „Der Herr der Ringe“ steht unter H
    const titel = (k) => k.querySelector(".karte-titel").textContent.replace(/^(der|die|das|the|ein|eine)\s+/i, "");
    const reihenfolge = new Map(karten.map((k, i) => [k, i])); // vom Build: neueste zuerst
    const alphabetisch = new Intl.Collator("de", { sensitivity: "base", numeric: true });
    const SORTIERUNG = {
      "": (a, b) => reihenfolge.get(a) - reihenfolge.get(b),
      "bewertung-ab": (a, b) => b.dataset.bewertung - a.dataset.bewertung || alphabetisch.compare(titel(a), titel(b)),
      "bewertung-auf": (a, b) => a.dataset.bewertung - b.dataset.bewertung || alphabetisch.compare(titel(a), titel(b)),
      "titel-auf": (a, b) => alphabetisch.compare(titel(a), titel(b)),
      "titel-ab": (a, b) => alphabetisch.compare(titel(b), titel(a)),
    };
    const leer = document.querySelector(".leer-gefiltert");

    const anwenden = () => {
      const f = Object.fromEntries(felder.map((s) => [s.name, s.value.trim()]));
      const woerter = normal(f.suche).split(/\s+/).filter(Boolean);
      let anzahl = 0;
      ruhe = null;
      const sortiert = [...karten].sort(SORTIERUNG[f.sortierung] ?? SORTIERUNG[""]);
      raster.append(...sortiert); // verschiebt die vorhandenen Karten in die neue Reihenfolge
      for (const karte of sortiert) {
        const d = karte.dataset;
        const passt =
          woerter.every((w) => d.suche.includes(w)) &&
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
      s.addEventListener(s.tagName === "INPUT" ? "input" : "change", anwenden);
    }
    filter.addEventListener("reset", () => setTimeout(anwenden));
    filter.hidden = false;
    anwenden();
  }
}
