# Luleå–Boden bostadsmarknad

Automatisk insamling av offentlig marknadsinformation för bostadsmarknaden i Luleå och Boden.

## Del 1 – Svensk Mäklarstatistik

Källa: kommunernas publika områdessidor hos Svensk Mäklarstatistik.

Insamlingen sparar för:
- Luleå och Boden
- bostadsrätter, villor och fritidshus
- 3 månader och 12 månader
- kr/m²
- medelpris
- antal sålda
- prisutveckling
- källans uppdateringsdatum

### Filer

`data/maklarstatistik/current.csv`
: senaste hämtningen.

`data/maklarstatistik/history.csv`
: historik per publiceringsdatum. Om samma publicering hämtas flera gånger ersätts samma observation i stället för att dupliceras.

### Uppdatering

GitHub Actions-workflow:
`.github/workflows/update_maklarstatistik.yml`

Körs automatiskt den 10:e varje månad kl. 07:15 UTC och kan även startas manuellt med **Run workflow**.

## Datakvalitet

Skriptet validerar att samtliga 12 förväntade kombinationer finns:
2 kommuner × 3 bostadstyper × 2 perioder.

Om källsidans struktur ändras avbryts körningen i stället för att ofullständiga data skrivs till historiken.

Fältet `prisutveckling_status` bevarar även Mäklarstatistiks markeringar `F` och `N` när ett numeriskt förändringstal saknas.

## Nästa steg

Del 2 blir löpande snapshots av bostadsannonser/utbud efter kontroll av lämplig datakälla, robots.txt och användarvillkor.


## Del 2 – Annonsmarknad utan otillåten scraping

Repot innehåller nu en färdig datastruktur för annonsdata, men ingen aktiv scraper mot sajter vars villkor förbjuder automatiserad hämtning.

Filer:
- `data/listings/current.csv` – senaste tillåtna snapshoten.
- `data/listings/history.csv` – historiska snapshots.
- `data/indicators/monthly.csv` – härledda månadsindikatorer.
- `src/build_indicators.py` – bygger indikatorerna från historiken.

Indikatorerna omfattar:
- aktiva objekt
- nya objekt
- borttagna objekt
- prissänkningar
- median utgångspris
- median pris per m²
- median annonstid

Workflowet `Build listing indicators` körs när `history.csv` ändras eller manuellt via GitHub Actions.

Ingen annonskälla ska kopplas in innan vi har en källa där automatiserad datainsamling är uttryckligen tillåten, till exempel via API, feed, licens eller annat tydligt medgivande.
