# Context

I am building a pipeline that generates synthetic legal/compliance documents for
**fictional** AI software tools. For each document type I need a YAML "style
guide" based on real documents. The style guide is inserted into LLM prompts,
so it must describe topics and conventions, not copy any real document.

This prompt covers ONE document type:
- Display name: Compliance & Certifications
- Slug: `compliance_and_certifications` (use this exact slug in file names and
  in the `document_type` field; it must match the doc type list in my config)

## Why this type is different

Real compliance documentation is usually NOT one long document. It is spread
across a landing page (a catalog of certification cards or logos), an FAQ,
and short detail pages per certification. My pipeline must still generate a
long, structured document. So the sources below are organized as **bundles**:
each company's pages together count as ONE source. One long-form compliance
whitepaper is included to show how the topic is written as a continuous
document.

## Source documents

Each source has a role. Bundles count as one source in all frequency counts.

**Source 1: long-form compliance whitepaper (structure reference)**
- aws_whitepaper: https://docs.aws.amazon.com/whitepapers/latest/aws-risk-and-compliance/welcome.html
  (cloud provider risk and compliance whitepaper, split across several HTML
  pages. Start here and follow the whitepaper's own table-of-contents links in
  order. Collect only pages that belong to this whitepaper. The page notes it is
  kept for historical reference; record that, and use it for structure only.)

**Source 2: atlassian bundle (collaboration SaaS)**
- landing: https://www.atlassian.com/trust/compliance
- faq: https://www.atlassian.com/trust/compliance/compliance-faq
- certification page: https://www.atlassian.com/trust/compliance/resources/soc2

**Source 3: slack bundle (collaboration SaaS with AI features)**
- landing: https://slack.com/trust/compliance

**Source 4: zoom bundle (communications SaaS with AI features)**
- landing: https://www.zoom.com/en/trust/legal-compliance/
- faq: https://www.zoom.com/en/trust/legal-compliance/faq/

**Source 5: google_cloud bundle (cloud provider)**
- catalog: https://cloud.google.com/security/compliance/offerings
- certification page: https://cloud.google.com/security/compliance/iso-42001
  (AI management system certification)

**Certification detail pages: use only a few.** Use at most **2 certification
detail pages per bundle** and at most **6 in total**. You may add a detail page
linked from a landing page only if the bundle has fewer than 2. When choosing,
prefer different kinds: one audit report (e.g. SOC 2), one ISO certification,
one AI-related certification. Do not collect every certification page; a few
are enough to see the repeating pattern.

Do not use any trust portal hosted on a third-party compliance platform (pages
that render only with JavaScript). If a page turns out to be JavaScript-only,
report it and skip it.

---

# Stage 1: Extract (no analysis, no summarizing)

For each URL:

1. Download the **raw HTML** with code (e.g. Python `requests`). Do not use a
   summarizing web-fetch tool.
2. Convert it to Markdown **preserving the heading hierarchy** (H1→#, H2→##,
   H3→###). Remove navigation, footers, cookie banners, tables of contents,
   logos without text, and scripts. Keep body text and tables.
3. Save each page as a separate file:
   `sources/compliance_and_certifications/[source]/[page].md`
   (e.g. `atlassian/landing.md`, `atlassian/faq.md`, `atlassian/cert_soc2.md`,
   `aws_whitepaper/01_welcome.md`, `aws_whitepaper/02_...md`).
4. Structure rules:
   - **Headings:** a paragraph whose entire text is bold (≤120 characters, not
     inside a list or table) becomes a heading one level below the heading
     above it. A bold label at the start of a paragraph becomes a subsection
     only if it introduces a distinct block of content.
   - **Numbering:** if headings are missing but text is numbered ("2.1", "(a)"),
     derive the structure from the numbering.
   - **Cards** (catalog grids): a card's title becomes a heading one level below
     the section it sits in, and the card's description becomes its body text.
     Cards with only a logo or a name and no description: keep them as a list of
     names under their section, not as headings.
   - **FAQ accordions:** each question becomes a heading and its answer becomes
     its body. If answers are not present in the HTML (loaded only on click),
     report it.
   - Mark every promoted or derived heading with `<!-- promoted -->` and every
     card heading with `<!-- card -->`.
5. With a script (not by reading), measure **per page** and **per source**
   (bundle or whitepaper):
   - top-level sections, total sections, leaf sections, maximum depth
   - body word count
   - word count of each leaf section, labeled by kind: `prose` (whitepaper and
     certification-page sections), `faq` (FAQ answers), `card` (card
     descriptions). Per source and per kind report min, p25, median, p75, max.
   Exclude non-content sections (link lists, "useful resources", sign-up
   boxes, community promotions) from the measurements, but keep them in the
   Markdown files.
6. Report problems instead of hiding them: blocked or truncated pages,
   JavaScript-only content, missing FAQ answers, invalid HTML, structure
   derived from numbering or cards.

Save all measurements, including every leaf's word count and kind, to
`sources/compliance_and_certifications/_measurements.json`.

**Then STOP** and show me two tables:
1. Per page: `source | page | top-level | leaf | depth | words | method | problems`
2. Per source and leaf kind: `source | kind | count | min / p25 / median / p75 / max`

Do not continue to Stage 2 until I confirm.

---

# Stage 2: Write the style guide

Set `typical_length.section_words` to the 25th–75th percentile of **prose and
faq** leaf word counts across all sources, rounded to integers. **Exclude
`card` leaves**: catalog card descriptions are too short to represent sections
of a full document. Report the card statistics separately in the chat.

Then, using ONLY the saved Markdown files and `_measurements.json`, write
`style_guides/compliance_and_certifications.yaml`:

```yaml
document_type: compliance_and_certifications
purpose: "1-2 sentences: what this document is for and who reads it"
scope: "what such documentation covers and excludes, how real versions differ
  (catalog page vs long-form whitepaper, SaaS vs cloud provider, AI vs non-AI),
  and that a complete document describes several certifications in turn"
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
certification_profile:
  description: "1 sentence: the pattern a section about one certification follows"
  content_points:
    - "short phrase"   # e.g. what the standard is, scope (products, plans,
                       # regions), type of assessment and assessor, coverage
                       # period or validity, how customers obtain the report
certification_catalog:
  - name: "..."        # generic standard or framework name, e.g. "SOC 2 Type II"
    category: "..."    # e.g. audit report, ISO certification, AI governance,
                       # privacy framework, sector regulation, regional program
tone_and_conventions: "..."
typical_length:
  section_words: [min, max]   # words per leaf section, integers
sources:
  - "..."   # every URL actually used
```

## Rules

**Topics**
- Each top-level section in the sources maps to a topic. Where sources have
  sections with similar names or similar content, merge them into one topic
  with a generic name and description written by you.
- **Folding and counting:** when sections are folded into one topic, count the
  topic once per **source** (bundle or whitepaper) that contains any of its
  origin sections. Report the folded count next to the counts of the origin
  sections it was built from.
- Former subsections, cards and FAQ questions become **content points**: short
  phrases of a few words, not sentences and not nested sections.
- **Do not create one topic per certification.** Individual certifications go
  into `certification_catalog`. What a section about a single certification
  covers goes into `certification_profile`. The topics describe the rest of the
  document (program overview, regulatory alignment, report access, shared
  responsibility, AI governance, and so on).
- **Core vs optional** (guideline, not a strict condition): appearing in at
  least half of the sources (folded count) is the default signal for core. A
  topic may also be core when it is a standard part of this document type or
  needed for a complete document. Once core, keep it core. Topics specific to
  one audience, region or provider type go to `optional_topics`. Mark rare
  content points inside a core topic with "(optional)".
- In the chat report, give a **topic frequency table**:
  `topic | core/optional | folded count | origin sections (count each)`, and
  name every topic made core below the half threshold, with the reason.
- Order `core_topics` in the order a long-form compliance document would
  present them, using the whitepaper as the main reference for order.
- Coverage: every content section in the sources must map to a topic, a
  content point, the certification profile or the certification catalog. Do
  not drop real content. Do not add topics that are not in the sources.

**Certification catalog**
- List the distinct standards, frameworks, regulations and programs that
  appear across the sources, with a category for each. Use generic names of
  the standards themselves (e.g. "ISO/IEC 27001", "SOC 2 Type II", "HIPAA").
- Do not include company-specific program names, product names or government
  authorization names tied to one company's product.

**No real companies and no source commentary**
- No company, product or service names anywhere in the file, except in the
  `sources` list.
- No commentary about the sources ("three of five sources", "one bundle...").

**Tone and conventions**
- Describe voice, formality, defined terms, cross-reference style, lists vs
  prose, tables, ALL CAPS usage (state plainly if it is not used), effective
  or "last updated" dates, and how claims of compliance are worded (e.g.
  "certified", "aligned with", "supports customers' compliance").
- Write it so it is usable on its own by a model writing a single section: my
  section generator receives only this field plus the section's description,
  not the topics or scope.
- Do NOT describe heading numbering, heading formats, cards or page layout
  (my pipeline generates a continuous document and adds headings itself).
- Do NOT describe linking to external pages, portals or URLs; refer only to
  "companion documents" or "compliance documentation available on request"
  generically.

**Length**
- `typical_length.section_words` follows the rule above (prose and faq leaves
  only), computed with a script from `_measurements.json`, rounded to
  integers, min < max.

**General**
- Write everything in your own words. Do not copy text.
- No structural numbers anywhere in the YAML, except
  `typical_length.section_words`.
- If something is unclear or the sources disagree, ask me (use AskUserQuestion
  if available) instead of deciding yourself.

## Checks before finishing

1. Search every field except `sources` for company and product names
   (including those of every source in this prompt) and confirm zero matches.
2. Parse the YAML to confirm it is valid, `document_type` equals
   `compliance_and_certifications`, and `typical_length.section_words` is a
   list of two integers with min < max.

## Report in chat (not in the YAML)

1. **Measurements for my config:** per source, min/max of top-level sections,
   leaf sections, depth and words; leaf word statistics by kind; outliers named
   and explained.
2. **Length rule applied:** the prose and faq numbers used, the card numbers
   excluded, and the resulting `[min, max]`.
3. **Mapping table:** `source section (source/page) → topic / content point /
   certification profile / catalog entry | dropped (reason)`
4. **Certification detail pages used:** which ones, and why they were chosen.
5. Anything you were unsure how to classify.
