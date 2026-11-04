# Context

I am building a pipeline that generates synthetic legal/compliance documents for
**fictional** AI software tools. For each document type I need a YAML "style
guide" based on real documents. The style guide is inserted into LLM prompts,
so it must describe topics and conventions, not copy any real document.

This prompt covers ONE document type:
- Display name: Compliance & Certifications  
- Slug: `compliance_and_certifications` (use this exact slug in file names and in the
  `document_type` field; it must match the doc type list in my pipeline config)

## Source documents

- [URL 1] : 


---

# Stage 1: Extract (no analysis, no summarizing)

For each URL:

1. Download the **raw HTML** with code (e.g. Python `requests`). Do not use a
   summarizing web-fetch tool.
2. Convert it to Markdown **preserving the heading hierarchy** (H1→#, H2→##,
   H3→###). Remove navigation, footers, cookie banners, tables of contents and
   scripts. Keep body text and tables.
3. Save it as `sources/terms_of_service/[company]_[variant].md`.
4. Structure rules:
   - A paragraph whose entire text is bold (≤120 characters, not inside a list
     or table) becomes a heading one level below the heading above it.
   - A bold label at the start of a paragraph ("Label: text…") becomes a
     subsection **only if it introduces a distinct block of content**. Labels
     inside lists or one-off inline emphasis stay as text.
   - If headings are missing but the text is numbered ("2.1", "(a)", "Article
     3"), derive the structure from the numbering.
   - Mark every promoted or derived heading with `<!-- promoted -->`.
5. With a script (not by reading), measure from the Markdown:
   - top-level sections, total sections, leaf sections
   - maximum depth
   - body word count
   - word count of **each leaf section** (body text under the leaf heading,
     excluding the heading itself); per document report min, max, median,
     25th percentile and 75th percentile
   Exclude non-content sections (translations, link lists, "useful resources")
   from the measurements, but keep them in the Markdown file.
6. Report problems instead of hiding them: blocked or truncated pages,
   JavaScript-only content, collapsed sections, invalid HTML, structure
   derived from numbering.

Save all measurements, including every leaf's word count, to
`sources/terms_of_service/_measurements.json`.

**Then STOP** and show me a table:
`document | top-level sections | leaf sections | max depth | words | leaf words min / p25 / median / p75 / max | method | problems`

Do not continue to Stage 2 until I confirm.

---

# Stage 2: Write the style guide

Set typical_length.section_words to the 25th–75th percentile of leaf-section word counts across all sources, rounded to integers.

Then, using ONLY the saved Markdown files and `_measurements.json`, write
`style_guides/terms_of_service.yaml`:

```yaml
document_type: terms_of_service
purpose: "1-2 sentences: what this document is for and between whom"
scope: "what such documents cover and exclude, and the main ways they differ"
core_topics:
  - name: "..."
    description: "1 sentence"
    content_points:
      - "short phrase"
optional_topics:
  - name: "..."
    description: "1 sentence"
    content_points:
      - "short phrase"
tone_and_conventions: "..."
typical_length:
  section_words: [min, max]   # words per leaf section, integers
sources: YAML list of the URL's
```

## Rules

**Topics**
- Each top-level section in the sources maps to a topic. Where sources have
  sections with similar names or similar content, merge them into one topic
  with a generic name and description written by you.
- **Folding and counting**: when sections with similar names or similar
  subject matter are folded into one topic, count the folded topic once per
  source document that contains ANY of its origin sections (top-level section
  or an equivalent subsection). Report the folded count next to the counts of
  the origin sections it was built from, so the effect of folding is visible.
- Former subsections become **content points**: short phrases of a few words,
  not sentences and not nested sections.
- **Core vs optional** (guideline, not a strict condition): appearing in at
  least half of the source documents (using the folded count) is the default
  signal for **core**, but it is not required. A topic may also be core when
  it is a standard part of this document type, appears widely as subsections,
  or is needed for a complete document of this type. Once you conclude a topic
  is core, keep it core; do not demote it later only because it falls below
  half. Topics that are rare and specific to one audience, region or product
  model go to `optional_topics`. Content points follow the same guideline:
  mark rare content points inside a core topic with "(optional)", unless they
  are substantial enough to be their own optional topic.
- In the chat report, give a **topic frequency table**:
  `topic | core/optional | folded count | origin sections (count each)` and
  name every topic made core below the half threshold, with the reason.
- Order `core_topics` in the most common order found in the sources.
- Coverage: every content section in the sources must map to a topic or content
  point. Do not drop real content. Do not add topics that are not in the sources.

**No real companies and no source commentary**
- No company, product or service names anywhere in the file, except in the sections sources that will have the urls from which the html was scraped
- No commentary about the sources ("three of five sources", "one document...").
- `scope`: describe the document type generically, including how real documents
  of this type differ (e.g. consumer vs business, AI-model provider vs
  platform, EU-first vs US-first).

**Tone and conventions**
- Describe voice, formality, defined terms, cross-reference style, lists vs
  prose, tables, ALL CAPS usage, effective dates and addenda.
- Write it so it is usable on its own by a model writing a single section: my
  section generator receives only this field plus the section's description,
  not the topics or scope.
- Do NOT describe heading numbering or heading formats (numbering is added by my
  pipeline).
- Do NOT describe linking to external pages, help centres or URLs; refer only to
  "companion documents" generically.

**Length**
- `typical_length.section_words` follows the rule I chose above, computed with
  a script from `_measurements.json`, rounded to integers, min < max.

**General**
- Write everything in your own words. Do not copy clause text.
- No structural numbers (section counts, word counts) anywhere in the YAML,
  except `typical_length.section_words`.
- If something is unclear or the sources disagree, ask me (use AskUserQuestion
  if available) instead of deciding yourself.

## Checks before finishing

1. Search the YAML for company and product names (including those of every
   source in this prompt) and confirm zero matches.
2. Parse the YAML to confirm it is valid, `document_type` equals
   `terms_of_service`, and `typical_length.section_words` is a list of two
   integers with min < max.

## Report in chat (not in the YAML)

1. **Measurements for my config**: min/max of top-level sections, leaf sections,
   depth, words and leaf words, with any outliers named and explained.
2. **Length rule applied**: the rule I chose, the input numbers, and the
   resulting `[min, max]`.
3. **Mapping table**: `source section (document) → topic / content point | dropped (reason)`
4. Anything you were unsure how to classify.