// Übersicht: Beim Überfahren einer Karte färbt sich das Raumlicht in deren Farbe.
const raster = document.querySelector(".raster");
if (raster) {
  const setzen = (karte) => {
    const farbe = karte ? getComputedStyle(karte).getPropertyValue("--leucht1") : "transparent";
    const grund = karte ? getComputedStyle(karte).getPropertyValue("--bg") : "";
    document.body.style.setProperty("--raumlicht", farbe);
    document.body.style.backgroundColor = grund;
  };
  for (const karte of raster.querySelectorAll(".karte")) {
    karte.addEventListener("mouseenter", () => setzen(karte));
    karte.addEventListener("focusin", () => setzen(karte));
  }
  raster.addEventListener("mouseleave", () => setzen(null));
}
