{
  "_description": "BookConfig — top-level book metadata. Mirrors packages/core/src/models/book.ts BookConfigSchema.",
  "id": "",
  "_id_description": "Unique book identifier (UUID or slug). Used as directory name under books/.",

  "title": "",
  "_title_description": "Human-readable book title.",

  "platform": "",
  "_platform_description": "Publishing platform: tomato | feilu | qidian | other. Determines default genre and pacing conventions.",

  "genre": "",
  "_genre_description": "Genre identifier matching a built-in or custom genre profile (e.g. xuanhuan, litrpg, cultivation).",

  "status": "incubating",
  "_status_description": "Book lifecycle status: incubating | outlining | active | paused | completed | dropped.",

  "targetChapters": 200,
  "_targetChapters_description": "Planned total number of chapters.",

  "chapterWordCount": 3000,
  "_chapterWordCount_description": "Target word count per chapter. Normalization band is +/-10% of this value.",

  "language": "zh",
  "_language_description": "Primary language: zh (Chinese) | en (English). Affects word counting, punctuation rules, and genre defaults.",

  "fanficMode": null,
  "_fanficMode_description": "Fan fiction mode, null for original fiction: canon | au | ooc | cp. Activates conditional audit dimensions 34-37.",

  "parentBookId": null,
  "_parentBookId_description": "For spinoff books, the ID of the parent book whose truth files are shared for canon consistency.",

  "createdAt": "",
  "_createdAt_description": "ISO 8601 datetime when the book was created.",

  "updatedAt": "",
  "_updatedAt_description": "ISO 8601 datetime when the book was last modified."
}
