#!/usr/bin/env bash
# Usage: gen-xhtml.sh <input.md> <output.xhtml>
# Converts markdown to XHTML 1.1 for EPUB 3.0

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input.md> <output.xhtml>" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="$2"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: Input file not found: $INPUT" >&2
  exit 1
fi

# Detect language from content
if grep -q '[一-龟]' "$INPUT"; then
  LANG="zh"
else
  LANG="en"
fi

# Extract title from first heading or filename
TITLE=$(grep -m1 '^#\s' "$INPUT" | sed 's/^#\s*//' || basename "$INPUT" .md)

# Check for pandoc
if command -v pandoc >/dev/null 2>&1; then
  # Use pandoc for conversion
  pandoc -f markdown -t html5 --standalone \
    --metadata title="$TITLE" \
    --metadata lang="$LANG" \
    -o "$OUTPUT" "$INPUT"

  # Convert HTML5 to XHTML 1.1
  sed -i.bak \
    -e 's|<!DOCTYPE html>|<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">|' \
    -e 's|<html|<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="'"$LANG"'"|' \
    -e 's|<meta charset="utf-8">|<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>|' \
    "$OUTPUT"
  rm -f "${OUTPUT}.bak"
else
  # Fallback: awk-based conversion
  awk -v title="$TITLE" -v lang="$LANG" '
  BEGIN {
    print "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    print "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.1//EN\" \"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd\">"
    print "<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"" lang "\">"
    print "<head><title>" title "</title><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"/></head>"
    print "<body>"
    in_para = 0
  }

  /^#{1,3}\s/ {
    if (in_para) { print "</p>"; in_para = 0 }
    level = length($0) - length(ltrim($0, "#"))
    gsub(/^#{1,3}\s*/, "")
    print "<h" level ">" $0 "</h" level ">"
    next
  }

  /^$/ {
    if (in_para) { print "</p>"; in_para = 0 }
    next
  }

  {
    line = $0
    # Bold: **text** -> <strong>text</strong>
    gsub(/\*\*([^*]+)\*\*/, "<strong>\\1</strong>", line)
    # Italic: *text* -> <em>text</em>
    gsub(/\*([^*]+)\*/, "<em>\\1</em>", line)

    if (!in_para) {
      printf "<p>"
      in_para = 1
    } else {
      printf " "
    }
    printf "%s", line
  }

  END {
    if (in_para) print "</p>"
    print "</body>"
    print "</html>"
  }

  function ltrim(s, c) {
    sub("^[" c "]+", "", s)
    return s
  }
  ' "$INPUT" > "$OUTPUT"
fi

echo "Generated XHTML: $OUTPUT"
