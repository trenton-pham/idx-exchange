# CRMLS Market Analysis @ IDX Exchange

## Tech Stack

- **Python 3.13** — primary programming language
- **Jupyter Notebook** — interactive data cleaning and exploration
- **pandas 3.0.3** — tabular data processing and CSV handling
- **GeoPandas 0.14.4** and **GeoJSON** — geographic filtering and California boundary data
- **Matplotlib 3.11.0** — histograms and box plots
- **Statsmodels 0.14.6** — descriptive statistical summaries
- **CRMLS data** — property listing and sold-record source data
- **FRED `MORTGAGE30US`** — weekly U.S. 30-year fixed mortgage-rate data

## Project Structure

```text
idx-exchange/
├── data/
│   ├── raw/               # Original monthly CRMLS CSV files
│   ├── processed/         # Combined residential listing and sold datasets
│   ├── filtered/          # Datasets after high-missingness columns are removed
│   ├── mortgage/          # Datasets enriched with monthly mortgage rates
│   └── city_boundaries/   # GeoJSON boundaries used for California filtering
├── docs/                  # Project reference documents
├── summary_stat/          # Generated descriptive-statistics CSV files
├── visuals/               # Generated histogram and box-plot PDFs
├── process.py             # Week 1 data processing
├── distribution.py        # Weeks 2–3 distribution analysis
├── validation.py          # Weeks 2–3 data validation
├── mortgage_fetch.py      # Weeks 2–3 mortgage-rate enrichment
├── clean.ipynb            # Weeks 4–5 data cleaning notebook
└── requirements.txt       # Python package versions
```

The `data/` directory represents the main pipeline stages. Files move from original monthly inputs in `raw/`, to combined files in `processed/`, to reduced-column files in `filtered/`, and finally to mortgage-enriched files in `mortgage/`. Generated statistics and charts are stored separately in `summary_stat/` and `visuals/`.

## Weekly Progress and File Purpose

| Week | File | Purpose |
| --- | --- | --- |
| Week 1 | `process.py` | Reads monthly listing and sold CSV files from January 2024 through June 2026, preferring `_filled` sold files when available. It combines the monthly files, keeps residential properties, and writes the resulting datasets to `data/processed/`. |
| Weeks 2–3 | `distribution.py` | Calculates descriptive statistics for selected price and property fields. It writes statistics to `summary_stat/` and creates histogram and box-plot PDFs in `visuals/`, excluding IQR-based outliers from the plots for readability. |
| Weeks 2–3 | `validation.py` | Examines property types and missing values, reports descriptive distributions for key sold-data fields, removes columns whose missing-value percentage exceeds the configured threshold, and saves the reduced datasets to `data/filtered/`. |
| Weeks 2–3 | `mortgage_fetch.py` | Fetches the FRED 30-year fixed mortgage-rate series, converts weekly rates to monthly averages, joins rates to sales by close month and listings by contract month, checks for unmatched records, and writes the intended enriched outputs to `data/mortgage/`. |
| Weeks 4–5 | `clean.ipynb` | Converts date fields, flags inconsistent transaction timelines, removes redundant columns, filters coordinates to California, removes invalid negative numeric values, and reviews row counts for the cleaned listing and sold datasets. |