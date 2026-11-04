# Automatisk synk av anonymiserad uthyrningsstatistik

Workflow: `.github/workflows/sync_villa_suitability.yml`. Varje fredag 08:10 UTC,
efter den privata fredagskörningen 06:30 UTC.

## Aktivera GitHub-behörigheten
Skapa ett **fine-grained personal access token** med:
- Repository access: endast `Lulea-statistik/uthyrning_villa` (privat).
- Repository permissions: `Actions: Read` och `Metadata: Read`.
- Ingen skrivbehörighet till privat eller publikt repository.
- Kort giltighetstid och en plan för förnyelse.

Lägg det i det **publika** repositoriets GitHub Actions repository secrets
under namnet `PRIVATE_RENTALS_READ_TOKEN` (Settings > Secrets and variables > Actions).
Värdet skrivs aldrig i workflow eller loggar. Det publika workflowets eget
`GITHUB_TOKEN` används för att skriva den godkända aggregerade JSON-filen
till det publika repositoriet.

Starta sedan workflowet `Sync anonymiserad uthyrningsklassning` med
`Run workflow` som första funktionstest.

När token saknas ger workflowet en tydlig status och uppdaterar inte statistik.
Om privatkörningen saknar lyckad export eller om JSON inte uppfyller strikt schema,
avbryts överföringen utan att den tidigare publika filen ersätts.
Värdena är klassificering av mastergrupper, **inte** aktuellt lediga bostäder.

En GitHub-token kan inte skapas eller läggas till av denna kod; den måste
registreras av en användare med behörighet att hantera Actions secrets.
