# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Personal academic website for Piotr Bystranowski, deployed to GitHub Pages at `bystranowski.github.io`. Pure static HTML/CSS/JS — no build tool, no framework, no npm.

## Pages

- `index.html` — landing/hero page
- `about.html` — biographical and research description
- `publications.html` — publication list organized by year and type
- `talks.html` — upcoming and past talks
- `cv.html` — embeds the PDF CV via `<iframe>`
- `contact.html` — contact information

## Styling

Single shared stylesheet: `style.css`. CSS variables defined in `:root`:
- `--primary: #002a5c` (dark navy)
- `--secondary: #0d6efd` (blue)

Pages sometimes add page-specific styles in an inline `<style>` block inside `<head>`.

## Navbar pattern

All pages share the same copy-pasted navbar HTML (no templating). When updating nav links, update every page. The burger menu for mobile is handled by an inline `<script>` at the bottom of each page (also copy-pasted).

## CV

The CV is a LaTeX document in `CV/CVnew.tex` compiled with pdflatex + biber. To compile:

```bash
cd CV && bash compile_ref.sh
```

The compiled PDF at `CV/Piotr_Bystranowski_CV.pdf` is what `cv.html` embeds and offers for download. After recompiling, copy it to `assets/Piotr_Bystranowski_CV.pdf` if needed (both locations exist).

## Update tool

`update.py` in the root is an interactive CLI for adding publications and talks:

```bash
python update.py
```

**Publications** — prompts for type, authors, title, venue, DOI, preprint URL, then:
- Appends a BibTeX entry to the appropriate `.bib` file in `CV/`
- Inserts a formatted `<li>` into `publications.html` at the correct year/type section
- Automatically recompiles the CV (pdflatex × 2 + biber) after writing

**Talks** — prompts for date (YYYY-MM-DD), display date, title, venue, invited/poster, then:
- Inserts `<li class="talk-item invited|poster" data-date="…">` into `talks.html`, sorted descending by date within the year
- If invited: also inserts `\talk{year}{title}{venue}` at the top of the Invited Talks section in `CVnew.tex` and recompiles the CV

`talks.html` uses JavaScript to auto-apply the `.past` CSS class (opacity 0.35) to any talk whose `data-date` attribute is earlier than today's date. Do not add `past` manually.

## Deployment

The site is served from this directory via GitHub Pages. No build step — push HTML/CSS/assets directly to `main`.

## Analytics

Plausible analytics script is included on every page with `data-domain="bystranowski.github.io"`.
