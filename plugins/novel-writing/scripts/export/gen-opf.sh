#!/usr/bin/env bash
# Usage: gen-opf.sh <book-dir> <xhtml-files-list>
# Generates content.opf (Open Packaging Format) for EPUB 3.0

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <book-dir> [xhtml-files-list]" >&2
  exit 1
fi

BOOK_DIR="$1"
BOOK_JSON="$BOOK_DIR/book.json"
OUTPUT="$BOOK_DIR/content.opf"

if [[ ! -f "$BOOK_JSON" ]]; then
  echo "Error: book.json not found: $BOOK_JSON" >&2
  exit 1
fi

# Read xhtml files from stdin or argument
if [[ $# -ge 2 ]]; then
  XHTML_FILES="$2"
else
  XHTML_FILES=$(mktemp)
  cat > "$XHTML_FILES"
  trap "rm -f $XHTML_FILES" EXIT
fi

# Extract metadata from book.json
TITLE=$(jq -r '.title // "Untitled"' "$BOOK_JSON")
AUTHOR=$(jq -r '.author // "Unknown Author"' "$BOOK_JSON")
LANGUAGE=$(jq -r '.language // "zh"' "$BOOK_JSON")
GENRE=$(jq -r '.genre // ""' "$BOOK_JSON")
CREATED=$(jq -r '.createdAt // ""' "$BOOK_JSON" | cut -d'T' -f1)

# Generate UUID
if command -v uuidgen >/dev/null 2>&1; then
  UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
elif command -v uuid >/dev/null 2>&1; then
  UUID=$(uuid -v4)
else
  UUID="urn:uuid:$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "00000000-0000-0000-0000-000000000000")"
fi

# Start OPF
cat > "$OUTPUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">$UUID</dc:identifier>
    <dc:title>$TITLE</dc:title>
    <dc:creator>$AUTHOR</dc:creator>
    <dc:language>$LANGUAGE</dc:language>
    <dc:date>$CREATED</dc:date>
    <dc:publisher>InkOS</dc:publisher>
EOF

if [[ -n "$GENRE" ]]; then
  echo "    <dc:subject>$GENRE</dc:subject>" >> "$OUTPUT"
fi

cat >> "$OUTPUT" <<EOF
    <meta property="dcterms:modified">$(date -u +"%Y-%m-%dT%H:%M:%SZ")</meta>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
EOF

# Add manifest items for each XHTML file
INDEX=1
while IFS= read -r xhtml; do
  [[ -z "$xhtml" ]] && continue
  BASENAME=$(basename "$xhtml")
  echo "    <item id=\"chapter-$INDEX\" href=\"chapters/$BASENAME\" media-type=\"application/xhtml+xml\"/>" >> "$OUTPUT"
  INDEX=$((INDEX + 1))
done < "$XHTML_FILES"

cat >> "$OUTPUT" <<EOF
  </manifest>
  <spine toc="ncx">
EOF

# Add spine itemrefs
INDEX=1
while IFS= read -r xhtml; do
  [[ -z "$xhtml" ]] && continue
  echo "    <itemref idref=\"chapter-$INDEX\"/>" >> "$OUTPUT"
  INDEX=$((INDEX + 1))
done < "$XHTML_FILES"

cat >> "$OUTPUT" <<EOF
  </spine>
  <guide>
    <reference type="toc" title="Table of Contents" href="nav.xhtml"/>
  </guide>
</package>
EOF

echo "Generated OPF: $OUTPUT"
