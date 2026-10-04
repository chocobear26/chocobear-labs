# Bilder und Videos für die Bilder-Strecke

## Name

`<app>--<titel>.<endung>`, zum Beispiel `waldlaeufer--boss-kampf.png`.
Querformat: `waldlaeufer--level-auswahl--breit.png`.

Apps: `mood-checker`, `juntos`, `waldlaeufer`, `farbdorf`, `lesespiel`, `aemtli`, `allgemein`.
Erlaubt: jpg, png, webp, gif (max. 5 MB) und mp4, webm (max. 40 MB).
Vorschaubild für ein Video: gleicher Name, aber `.jpg`/`.png`.

## Vor dem Hochladen, immer

1. **Säubern** mit `tools/bereinigen.sh <datei> <app> <titel>`. Entfernt GPS, Gerät, Datum und bei Videos die Tonspur.
   Nie direkt über die GitHub-Webseite hochladen: was einmal im Repo war, bleibt in der Historie.
2. **Selbst ansehen:** keine Namen, keine Gesichter, keine Fotos von Personen, keine Benachrichtigungen,
   keine Uhrzeit oder Akku-Leiste mit erkennbaren Infos, keine Adressen oder Links.
3. **Beschriftung** (optional) und Reihenfolge in `texte.json`:
   `[{"datei": "waldlaeufer--boss-kampf.png", "text": "Der erste Boss"}]`

Die GitHub Action prüft jede Datei erneut und veröffentlicht nichts, das durchfällt.
