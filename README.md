# CRMLS Market Analysis @ IDX Exchange

This project prepares California Regional Multiple Listing Service (CRMLS) listing and sales data for market analysis. The workflow combines monthly source files, validates and profiles the data, enriches records with mortgage rates, cleans invalid values, engineers analysis-ready features, and filters sale-price outliers.

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
│   ├── cleaned/           # Cleaned listing and sold datasets
│   ├── post_outlier/      # Sold data after outlier filtering
│   └── city_boundaries/   # GeoJSON boundaries used for California filtering
├── docs/                  # Project reference documents
├── summary_stat/          # Generated descriptive-statistics CSV files
├── visuals/               # Generated histogram and box-plot PDFs
├── process.py             # Week 1 data processing
├── distribution.py        # Weeks 2–3 distribution analysis
├── validation.py          # Weeks 2–3 data validation
├── mortgage_fetch.py      # Weeks 2–3 mortgage-rate enrichment
├── clean.ipynb            # Weeks 4–5 data cleaning notebook
├── clean.py               # Week 6 reusable cleaning script
├── feature_engineer.ipynb # Week 6 feature engineering and summaries
├── outlier.py             # Week 7 sale-price outlier filtering
└── requirements.txt       # Python package versions
```

The `data/` directory represents the main pipeline stages. Files move from original monthly inputs in `raw/`, to combined files in `processed/`, reduced-column files in `filtered/`, mortgage-enriched files in `mortgage/`, and cleaned outputs in `cleaned/`. The `post_outlier/` directory contains sold data after the current price-outlier filter is applied. Generated statistics and charts are stored separately in `summary_stat/` and `visuals/`.

## Weekly Progress and File Purpose

| Week | File | Purpose |
| --- | --- | --- |
| Week 1 | `process.py` | Reads monthly listing and sold CSV files from January 2024 through June 2026, preferring `_filled` sold files when available. It combines the monthly files, keeps residential properties, and writes the resulting datasets to `data/processed/`. |
| Weeks 2–3 | `distribution.py` | Calculates descriptive statistics for selected price and property fields. It writes statistics to `summary_stat/` and creates histogram and box-plot PDFs in `visuals/`, excluding IQR-based outliers from the plots for readability. |
| Weeks 2–3 | `validation.py` | Examines property types and missing values, reports descriptive distributions for key sold-data fields, removes columns whose missing-value percentage exceeds the configured threshold, and saves the reduced datasets to `data/filtered/`. |
| Weeks 2–3 | `mortgage_fetch.py` | Fetches the FRED 30-year fixed mortgage-rate series, converts weekly rates to monthly averages, joins rates to sales by close month and listings by contract month, checks for unmatched records, and writes the intended enriched outputs to `data/mortgage/`. |
| Weeks 4–5 | `clean.ipynb` | Converts date fields, flags inconsistent transaction timelines, removes redundant columns, filters coordinates to California, removes invalid negative numeric values, and reviews row counts for the cleaned listing and sold datasets. |
| Week 4-5 | `clean.py` | Converts the notebook cleaning workflow into a reusable script; writes cleaned files into `data/cleaned/`. |
| Week 6 | `feature_engineer.ipynb` | Creates price ratios, price per square foot, year/month fields, and listing-to-contract and contract-to-close durations; summarizes key market measures by property subtype, county, MLS area, listing office, and buyer office. |
| Week 6 | `feature_engineer.py` | Converts the notebook feature engineering workflow into a reusable script; writes feature engineered files into `data/feature_engineer/`.  |
| Week 7 | `outlier.py` | Applies a three-IQR boundary to `ClosePrice`, reports row counts before and after filtering, and writes the resulting sold dataset to `data/post_outlier/`. |
