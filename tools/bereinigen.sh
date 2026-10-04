#!/usr/bin/env bash
# Saeubert ein Bild oder Video und legt es passend benannt in media/ ab.
# Laeuft auf dem Mac. Einmalig noetig:  brew install exiftool ffmpeg
#
#   tools/bereinigen.sh <datei> <app> <titel> [breit]
#   tools/bereinigen.sh ~/Desktop/IMG_1234.PNG waldlaeufer boss-kampf
#
# Was passiert:
#   Bilder: HEIC wird zu JPG, max. 1600 px, ALLE Metadaten entfernt (GPS, Geraet, Datum).
#   Videos: max. 1080 px, ALLE Metadaten und die TONSPUR entfernt (Mikrofon!), als MP4.
# Danach prueft tools/build_media.py --check, ob alles sauber ist.
# Bitte trotzdem jedes Bild selbst ansehen: Namen, Gesichter, Benachrichtigungen,
# Uhrzeit-Leiste, Fotos im Hintergrund. Metadaten kann ein Skript finden, Inhalte nicht.
set -euo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,7p' "$0"; exit 1
fi

QUELLE="$1"; APP="$2"; TITEL="$3"; BREIT="${4:-}"
ZIEL_DIR="$(cd "$(dirname "$0")/.." && pwd)/media"

for t in exiftool ffmpeg; do
  command -v "$t" >/dev/null || { echo "$t fehlt: brew install exiftool ffmpeg"; exit 1; }
done
[ -f "$QUELLE" ] || { echo "Datei nicht gefunden: $QUELLE"; exit 1; }
[[ "$TITEL" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "Titel nur aus a-z, 0-9 und Bindestrich, z.B. boss-kampf"; exit 1; }

BASIS="${APP}--${TITEL}"
[ "$BREIT" = "breit" ] && BASIS="${BASIS}--breit"

EXT="$(echo "${QUELLE##*.}" | tr '[:upper:]' '[:lower:]')"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

case "$EXT" in
  heic|heif|jpg|jpeg|png|webp)
    if [ "$EXT" = "heic" ] || [ "$EXT" = "heif" ]; then
      sips -s format jpeg "$QUELLE" --out "$TMP/bild.jpg" >/dev/null; EXT=jpg; QUELLE="$TMP/bild.jpg"
    fi
    [ "$EXT" = "jpeg" ] && EXT=jpg
    ZIEL="$ZIEL_DIR/$BASIS.$EXT"
    cp "$QUELLE" "$TMP/arbeit.$EXT"
    sips -Z 1600 "$TMP/arbeit.$EXT" >/dev/null
    exiftool -q -all= -overwrite_original "$TMP/arbeit.$EXT"
    mv "$TMP/arbeit.$EXT" "$ZIEL"
    ;;
  mov|mp4|m4v|webm)
    ZIEL="$ZIEL_DIR/$BASIS.mp4"
    ffmpeg -loglevel error -y -i "$QUELLE" \
      -map 0:v:0 -an -map_metadata -1 -map_chapters -1 \
      -vf "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))'" \
      -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart \
      "$TMP/video.mp4"
    exiftool -q -all= -overwrite_original "$TMP/video.mp4" || true
    mv "$TMP/video.mp4" "$ZIEL"
    ;;
  *)
    echo "Dateityp .$EXT wird nicht unterstuetzt"; exit 1 ;;
esac

echo "Gesaeubert: media/$(basename "$ZIEL")"
python3 "$(dirname "$0")/build_media.py" --check
echo "Jetzt das Bild selbst ansehen. Erst dann committen."
