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

## Uthyrning av småhus – aggregerad publicering

En offentlig undersida, `docs/uthyrning_smahus.html`, visar enbart aggregerade uppgifter från det **privata** arbetsrepositoriet `Lulea-statistik/uthyrning_villa`. Undersidan länkas från huvudsidans navigering.

Publicerat dataunderlag: `docs/villa_rental_aggregates.json`, senast dokumenterat 2026-10-16. Underlaget innehåller datum, antal identifierade unika objekt, antal med verifierad fullständig adress samt (när tillgängligt) uppdelning på ordinarie uthyrning och korttidsuthyrning.

**Integritet:** Publicera inte `data/objects.csv`, `data/listings.csv`, annons-ID, detaljerade adresser eller andra interna uppgifter från den privata källan. Enbart de godkända aggregerade snapshotfälten kopieras manuellt till den offentliga JSON-filen; det finns ingen automatisk koppling från den publika webbplatsen till det privata repositoriet.

**Metod:** Serien över identifierade objekt är hittills inte en jämförbar serie över aktiva/lediga småhus. Söktäckningen har förbättrats mellan kartläggningarna. Publicera därför inte ökningen som faktisk marknadstillväxt. Uppdatera metoddokumentationen om en stabil, jämförbar aktiv-serie etableras.

## Överlappning mellan uthyrningswebbplatser

Undersidan `docs/uthyrning_smahus.html` innehåller också ett aggregerat överlappningsavsnitt. Den offentliga datafilen `docs/villa_site_overlap.json` har skapats utifrån dokumenterade `object_id`–`source`-kopplingar i det privata projektets `data/listings.csv` (senast observerade annonser 2026-10-16).

**Skilj på täckningsnivåerna (2026-10-16):**
- 66 totalt identifierade uthyrningsobjekt i bevakningen,
- 20 särskilt granskade objekt i objektmastern,
- **10** objekt med dokumenterade annonskopplingar i `listings.csv`,
- 24 registrerade annonsrader; 22 unika webbplats–objekt-kombinationer,
- 9 av dessa 10 objekt förekommer på minst två olika webbplatser.

De 10 objekten är en **selektivt dokumenterad delmängd**, inte ett slumpmässigt urval. **9/10 får inte presenteras som en andel för de 66 identifierade objekten eller för hela marknaden.**

Den publika JSON-filen innehåller endast:
- täckningstal och källans datum,
- antal unika objekt respektive annonsrader per webbplats,
- antal gemensamma unika objekt per webbplatspar,
- fördelning efter antal olika webbplatser per objekt.

Ingen publik objektlista, adress, annonsnyckel, anonymt objekt-ID eller per-objekt-dubblettmönster publiceras. Webbplatsparens procenttal är Jaccard: `gemensamma objekt / (objekt på A + objekt på B - gemensamma objekt)`.

**Uppdatering:** Då ursprungsrepositoriet är privat måste en behörig aktör härleda och granska aggregeringen från dess aktuella `listings.csv` och därefter uppdatera `docs/villa_site_overlap.json` i detta publika repo. Ett automatiserat flöde från privat till publikt har **inte** aktiverats. Råa objekt- och annonsfiler ska aldrig kopieras hit. Observationerna visar dokumenterade annonser, inte säkert aktuella lediga objekt. Vid ny kartläggning ska täckning och jämförbarhet dokumenteras på nytt.
