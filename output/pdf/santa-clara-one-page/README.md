# Santa Clara Market Overview — one-page LaTeX report

The report uses a custom 20 × 11.5 inch page and three columns. All original narrative text and four takeaway bullets are preserved. The six screenshots, containing nine charts, are extracted from the source PDF without resampling; chart text remains part of those images. No market claims or grammatical inconsistencies have been revised.

## Compile

Keep `santa-clara-one-page.tex` and `assets/` in the same directory. Run:

```sh
pdflatex santa-clara-one-page.tex
```

XeLaTeX or Tectonic can also compile the file. For Overleaf, upload the ZIP archive and set `santa-clara-one-page.tex` as the main document.

The precompiled PDF was verified to contain one page, all original narrative sentences, and all six screenshots.
