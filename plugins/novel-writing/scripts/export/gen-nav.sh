#!/usr/bin/env bash
# Usage: gen-nav.sh <book-dir> <xhtml-files-list>
# Generates toc.ncx and nav.xhtml for EPUB 3.0

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <book-dir> [xhtml-files-list]" >&2
  exit 1
fi

BOOK_DIR="$1"
BOOK_JSON="$BOOK_DIR/book.json"
NCX_OUTPUT="$BOOK_DIR/toc.ncx"
NAV_OUTPUT="$BOOK_DIR/nav.xhtml"

if [[ ! -f "$BOOK_JSON" ]]; then
  echo "Error: book.json not found: $BOOK_JSON" >&2
  exit 1
fi

# Read xhtml files
if [[ $# -ge 2 ]]; then
  XHTML_FILES="$2"
else
  XHTML_FILES=$(mktemp)
  cat > "$XHTML_FILES"
  trap "rm -f $XHTML_FILES" EXIT
fi

TITLE=$(jq -r '.title // "Untitled"' "$BOOK_JSON")
LANGUAGE=$(jq -r '.language // "zh"' "$BOOK_JSON")

# Generate UUID for NCX
if command -v uuidgen >/dev/null 2>&1; then
  UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
elif command -v uuid >/dev/null 2>&1; then
  UUID=$(uuid -v4)
else
  UUID="00000000-0000-0000-0000-000000000000"
fi

# Generate NCX
cat > "$NCX_OUTPUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="$UUID"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>$TITLE</text>
  </docTitle>
  <navMap>
EOF

# Generate NAV
cat > "$NAV_OUTPUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="$LANGUAGE">
<head>
  <title>Table of Contents</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
  <nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">
    <h1>Table of Contents</h1>
    <ol>
EOF

# Process each XHTML file
INDEX=1
while IFS= read -r xhtml; do
  [[ -z "$xhtml" ]] && continue

  BASENAME=$(basename "$xhtml")

  # Extract title from XHTML (first h1, h2, or h3)
  if [[ -f "$xhtml" ]]; then
    CHAPTER_TITLE=$(grep -m1 -oE '<h[123]>[^<]+' "$xhtml" 2>/dev/null | sed 's/<h[123]>//' || echo "Chapter $INDEX")
  else
    CHAPTER_TITLE="Chapter $INDEX"
  fi

  # Add to NCX
  cat >> "$NCX_OUTPUT" <<EOF
    <navPoint id="chapter-$INDEX" playOrder="$INDEX">
      <navLabel>
        <text>$CHAPTER_TITLE</text>
      </navLabel>
      <content src="chapters/$BASENAME"/>
    </navPoint>
EOF

  # Add to NAV
  echo "      <li><a href=\"chapters/$BASENAME\">$CHAPTER_TITLE</a></li>" >> "$NAV_OUTPUT"

  INDEX=$((INDEX + 1))
done < "$XHTML_FILES"

# Close NCX
cat >> "$NCX_OUTPUT" <<EOF
  </navMap>
</ncx>
EOF

# Close NAV
cat >> "$NAV_OUTPUT" <<EOF
    </ol>
  </nav>
</body>
</html>
EOF

echo "Generated NCX: $NCX_OUTPUT"
echo "Generated NAV: $NAV_OUTPUT"
