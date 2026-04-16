---
name: novel-export
description: Export book to TXT, Markdown, or EPUB
---

# /novel-export — Book Export

## Usage
/novel-export --format <txt|md|epub> [--approved-only] [--output <path>] [--book <id>]

## Formats

### TXT
Plain text with chapter separators.

### Markdown
Markdown with proper formatting.

### EPUB (REQ-F-49, REQ-F-50)
EPUB 3.0 with metadata, TOC, and chapter formatting.

**Process:**
1. Collect chapters (approved-only or all)
2. Run epub-assemble.sh script
3. Generate EPUB file
4. Report output path

## Options
- `--format <fmt>`: Export format (txt/md/epub)
- `--approved-only`: Export only approved chapters (REQ-F-51)
- `--output <path>`: Output file path
- `--book <id>`: Target book

## Implementation Steps

### Step 1: Load Book Config
```bash
BOOK_DIR="books/$BOOK_ID"
BOOK_JSON="$BOOK_DIR/book.json"

if [[ ! -f "$BOOK_JSON" ]]; then
  echo "Error: Book not found: $BOOK_ID"
  exit 1
fi

eval $(python3 -c "
import json
d = json.load(open('$BOOK_JSON'))
print(f'BOOK_TITLE=\"{d.get(\"title\", \"\")}\"')
print(f'BOOK_AUTHOR=\"{d.get(\"author\", \"Unknown\")}\"')
print(f'BOOK_LANGUAGE=\"{d.get(\"language\", \"\")}\"')
print(f'BOOK_GENRE=\"{d.get(\"genre\", \"\")}\"')
")
```

### Step 2: Collect Chapters
```bash
CHAPTERS_DIR="$BOOK_DIR/chapters"

# Chapter lookup uses shared utility (scripts/lib/chapter_utils.py)
# Usage: python3 $.plugin.directory/scripts/lib/chapter_utils.py find "$CHAPTERS_DIR" "$num"

if [[ "$APPROVED_ONLY" == true ]]; then
  # Read chapter-meta.json to filter approved chapters (backward compat: fall back to review-status.json)
  CHAPTER_META="$BOOK_DIR/story/state/chapter-meta.json"
  # Backward compat: fall back to review-status.json if chapter-meta.json not found
  REVIEW_STATUS="$BOOK_DIR/review-status.json"
  if [[ -f "$CHAPTER_META" ]]; then
    CHAPTER_NUMBERS=$(python3 -c "
import json
d = json.load(open('$CHAPTER_META'))
for c in d.get('chapters', []):
    if c.get('status') == 'approved':
        print(c['number'])
")
    for num in $CHAPTER_NUMBERS; do
      python3 $.plugin.directory/scripts/lib/chapter_utils.py find "$CHAPTERS_DIR" "$num"
    done | sort
  elif [[ -f "$REVIEW_STATUS" ]]; then
    CHAPTER_NUMBERS=$(python3 -c "
import json
d = json.load(open('$REVIEW_STATUS'))
for c in d.get('chapters', []):
    if c.get('status') == 'approved':
        print(c['number'])
")
    for num in $CHAPTER_NUMBERS; do
      python3 $.plugin.directory/scripts/lib/chapter_utils.py find "$CHAPTERS_DIR" "$num"
    done | sort
  else
    echo "Warning: No chapter meta or review status found, exporting all chapters"
    find "$CHAPTERS_DIR" -name "*.md" | sort
  fi
else
  find "$CHAPTERS_DIR" -name "*.md" | sort
fi
```

### Step 3: Export by Format

#### TXT Export
```bash
OUTPUT_FILE="${OUTPUT_PATH:-$BOOK_DIR/$BOOK_TITLE.txt}"

{
  echo "$BOOK_TITLE"
  echo "作者: $BOOK_AUTHOR"
  echo ""
  echo "================================"
  echo ""
  
  for chapter_file in $CHAPTER_FILES; do
    BASENAME=$(basename "$chapter_file" .md)
    CHAPTER_NUM=$(echo "$BASENAME" | grep -oE '^[0-9]+' | sed 's/^0*//')
    if [ -z "$CHAPTER_NUM" ]; then
      CHAPTER_NUM=$(echo "$BASENAME" | sed 's/chapter-0*\([0-9]*\)/\1/')
    fi
    CHAPTER_TITLE=$(head -n 1 "$chapter_file" | sed 's/^#\+\s*//')
    
    echo ""
    echo "第${CHAPTER_NUM}章 $CHAPTER_TITLE"
    echo ""
    tail -n +2 "$chapter_file"
    echo ""
    echo "--------------------------------"
  done
} > "$OUTPUT_FILE"
```

#### Markdown Export
```bash
OUTPUT_FILE="${OUTPUT_PATH:-$BOOK_DIR/$BOOK_TITLE.md}"

{
  echo "# $BOOK_TITLE"
  echo ""
  echo "**作者**: $BOOK_AUTHOR"
  echo ""
  echo "---"
  echo ""
  
  for chapter_file in $CHAPTER_FILES; do
    cat "$chapter_file"
    echo ""
    echo "---"
    echo ""
  done
} > "$OUTPUT_FILE"
```

#### EPUB Export (REQ-F-49, REQ-F-50)
```bash
OUTPUT_FILE="${OUTPUT_PATH:-$BOOK_DIR/$BOOK_TITLE.epub}"

# Run epub-assemble.sh script
scripts/export/epub-assemble.sh \
  "$BOOK_DIR" \
  "$OUTPUT_FILE" \
  $([ "$APPROVED_ONLY" == true ] && echo "" || echo "--all")
```

The epub-assemble.sh script:
1. Creates EPUB directory structure (META-INF/, chapters/)
2. Converts chapters to XHTML using gen-xhtml.sh
3. Generates content.opf with metadata
4. Generates navigation files (toc.ncx, nav.xhtml)
5. Creates mimetype file
6. Creates container.xml
7. Packages as ZIP with correct compression

### Step 4: Report Results

#### TXT/Markdown Output
```
Exporting to TXT...

Collecting chapters:
✅ 50 approved chapters (165,000 words)

Export complete:
- Format: TXT
- File: books/book-001/破灭星辰.txt
- Size: 512 KB
- Chapters: 50
- Words: 165,000
```

#### EPUB Output (REQ-F-49)
```
Exporting to EPUB...

Collecting chapters:
✅ 50 approved chapters (165,000 words)

Generating EPUB:
✅ Converting chapters to XHTML
✅ Generating content.opf
✅ Generating navigation (toc.ncx, nav.xhtml)
✅ Assembling EPUB package

Export complete:
- Format: EPUB 3.0
- File: books/book-001/破灭星辰.epub
- Size: 1.2 MB
- Chapters: 50
- Words: 165,000
```

## EPUB Metadata (REQ-F-50)

The content.opf file includes:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:generated-uuid</dc:identifier>
    <dc:title>破灭星辰</dc:title>
    <dc:creator>作者名</dc:creator>
    <dc:language>zh</dc:language>
    <dc:subject>玄幻</dc:subject>
    <meta property="dcterms:modified">2026-04-14T12:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="chapter-0001" href="chapters/chapter-0001.xhtml" media-type="application/xhtml+xml"/>
    ...
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter-0001"/>
    ...
  </spine>
</package>
```

Navigation files (toc.ncx and nav.xhtml) provide table of contents with chapter titles.

## Error Handling

### No Chapters Found
```
Error: No chapters found to export

Options:
1. Write chapters first: /novel-write
2. Import chapters: /novel create --import <file>
```

### No Approved Chapters (--approved-only)
```
Error: No approved chapters found

Current state:
- Total chapters: 50
- Approved chapters: 0

Options:
1. Approve chapters: /novel-review --approve-all
2. Export all chapters: /novel-export --format epub (without --approved-only)
```

### EPUB Assembly Failed
```
Error: EPUB assembly failed

Details: [script error message]

Troubleshooting:
1. Check chapter files are valid markdown
2. Verify book.json contains required metadata
3. Check disk space for temporary files
```

### Output File Exists
```
Warning: Output file already exists: books/book-001/破灭星辰.epub

Overwrite? (yes/no):
```

## Approved-Only Behavior (REQ-F-51)

When `--approved-only` flag is set:
1. Read chapter-meta.json to filter approved chapters (backward compat: fall back to review-status.json)
2. Only export chapters with `status: "approved"` in ChapterMeta
3. Skip pending or unapproved chapters
4. Report count of approved vs total chapters

Example:
```
Collecting chapters:
✅ 45 approved chapters (148,500 words)
⏭️  Skipped 5 pending chapters

Export includes only approved chapters.
```

## Integration with Review System

Export respects review status:
- Approved chapters: included in --approved-only export
- Pending chapters: excluded from --approved-only export
- No review status file: all chapters treated as approved

## Performance Considerations

- TXT/Markdown export: Fast (< 1 second for 200 chapters)
- EPUB export: Moderate (5-10 seconds for 200 chapters)
- EPUB validation: Optional (use epubcheck if available)

## EPUB Validation

If epubcheck is installed:
```bash
if command -v epubcheck >/dev/null 2>&1; then
  echo "Validating EPUB..."
  epubcheck "$OUTPUT_FILE"
fi
```

## Language Support

- Chinese (zh): UTF-8 encoding, vertical text support (optional)
- English (en): UTF-8 encoding, standard horizontal text
- Metadata language tag matches book.json language field

## Output Path Resolution

Default output paths:
- TXT: `books/<id>/<title>.txt`
- Markdown: `books/<id>/<title>.md`
- EPUB: `books/<id>/<title>.epub`

Custom output path:
```bash
/novel-export --format epub --output /path/to/custom.epub
```

## File Size Estimates

- TXT: ~3 KB per 1000 words
- Markdown: ~3.5 KB per 1000 words
- EPUB: ~8 KB per 1000 words (includes XHTML overhead + metadata)

For 200 chapters × 3000 words = 600,000 words:
- TXT: ~1.8 MB
- Markdown: ~2.1 MB
- EPUB: ~4.8 MB
