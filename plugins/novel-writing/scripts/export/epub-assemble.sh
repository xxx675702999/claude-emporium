#!/usr/bin/env bash
# Usage: epub-assemble.sh <book-dir> <output.epub> [--all]
# Assembles a complete EPUB 3.0 package from book directory

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <book-dir> <output.epub> [--all]" >&2
  exit 1
fi

BOOK_DIR="$1"
OUTPUT_EPUB="$2"
APPROVED_ONLY=true

if [[ "${3:-}" == "--all" ]]; then
  APPROVED_ONLY=false
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOK_JSON="$BOOK_DIR/book.json"
CHAPTERS_DIR="$BOOK_DIR/chapters"
WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

if [[ ! -f "$BOOK_JSON" ]]; then
  echo "Error: book.json not found: $BOOK_JSON" >&2
  exit 1
fi

if [[ ! -d "$CHAPTERS_DIR" ]]; then
  echo "Error: chapters directory not found: $CHAPTERS_DIR" >&2
  exit 1
fi

echo "Assembling EPUB from: $BOOK_DIR"
echo "Output: $OUTPUT_EPUB"

# Create EPUB structure
mkdir -p "$WORK_DIR/META-INF"
mkdir -p "$WORK_DIR/chapters"

# Step 1: Find chapter files
CHAPTER_FILES=$(mktemp)
if [[ "$APPROVED_ONLY" == true ]]; then
  # Read chapter index to filter approved chapters
  INDEX_FILE="$BOOK_DIR/chapter-index.json"
  if [[ -f "$INDEX_FILE" ]]; then
    jq -r '.[] | select(.status == "approved") | .number' "$INDEX_FILE" | while read -r num; do
      printf -v padded "%04d" "$num"
      find "$CHAPTERS_DIR" -name "${padded}*.md" -print -quit
    done > "$CHAPTER_FILES"
  else
    find "$CHAPTERS_DIR" -name "[0-9][0-9][0-9][0-9]*.md" | sort > "$CHAPTER_FILES"
  fi
else
  find "$CHAPTERS_DIR" -name "[0-9][0-9][0-9][0-9]*.md" | sort > "$CHAPTER_FILES"
fi

CHAPTER_COUNT=$(wc -l < "$CHAPTER_FILES" | tr -d ' ')
if [[ "$CHAPTER_COUNT" -eq 0 ]]; then
  echo "Error: No chapters found to export" >&2
  exit 1
fi

echo "Found $CHAPTER_COUNT chapters"

# Step 2: Convert chapters to XHTML
XHTML_FILES=$(mktemp)
INDEX=1
while IFS= read -r md_file; do
  [[ -z "$md_file" ]] && continue
  printf -v padded "%04d" "$INDEX"
  XHTML_FILE="$WORK_DIR/chapters/chapter-${padded}.xhtml"
  echo "Converting: $(basename "$md_file")"
  "$SCRIPT_DIR/gen-xhtml.sh" "$md_file" "$XHTML_FILE"
  echo "$XHTML_FILE" >> "$XHTML_FILES"
  INDEX=$((INDEX + 1))
done < "$CHAPTER_FILES"

# Step 3: Generate OPF
echo "Generating content.opf"
"$SCRIPT_DIR/gen-opf.sh" "$WORK_DIR" "$XHTML_FILES"

# Step 4: Generate navigation
echo "Generating navigation files"
"$SCRIPT_DIR/gen-nav.sh" "$WORK_DIR" "$XHTML_FILES"

# Step 5: Create mimetype (must be first, uncompressed)
echo -n "application/epub+zip" > "$WORK_DIR/mimetype"

# Step 6: Create container.xml
cat > "$WORK_DIR/META-INF/container.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
EOF

# Step 7: Package as EPUB (ZIP with specific order)
echo "Packaging EPUB"
cd "$WORK_DIR"

# Remove existing output
rm -f "$OUTPUT_EPUB"

# Add mimetype first (stored, no compression)
zip -0 -X "$OUTPUT_EPUB" mimetype

# Add remaining files (compressed)
zip -r -9 "$OUTPUT_EPUB" META-INF/ content.opf toc.ncx nav.xhtml chapters/

cd - >/dev/null

# Validate mimetype position
if command -v unzip >/dev/null 2>&1; then
  FIRST_FILE=$(unzip -l "$OUTPUT_EPUB" | awk 'NR==4 {print $4}')
  if [[ "$FIRST_FILE" != "mimetype" ]]; then
    echo "Warning: mimetype is not the first file in EPUB" >&2
  fi
fi

echo "EPUB created successfully: $OUTPUT_EPUB"
echo "Total chapters: $CHAPTER_COUNT"

# Cleanup
rm -f "$CHAPTER_FILES" "$XHTML_FILES"
