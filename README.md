# CRMLS Market Analysis @ IDX Exchange

This project turns monthly California Regional Multiple Listing Service (CRMLS) listing and closed-sale exports into analysis-ready datasets for market, competitive, and predictive analysis. The workflow supports resumable Trestle API extraction, residential-property filtering, data-quality validation, mortgage-rate enrichment, geographic cleaning, feature engineering, outlier filtering, Tableau dashboards, and exploratory sale-price modeling.

CRMLS records and all derived datasets are confidential. The `data/`, `docs/`, and local environment files are intentionally ignored by Git.

## Current Capabilities

- Fetch any inclusive month range from the CoreLogic Trestle WebAPI and save separate listing and sold CSVs.
- Resume historical backfills by skipping completed files, or safely refresh files with `--force`.
- Validate metadata, pagination, record counts, listing-key uniqueness, date boundaries, and closed-sale status before publishing an export.
- Discover all available monthly listing/sold pairs automatically, including preferred `_filled` sold files, without a hard-coded ending month.
- Filter to residential California properties and valid California ZIP codes.
- Flag invalid transaction timelines, negative values, small living areas, coordinates outside California, and coordinates that do not match the reported county.
- Add monthly 30-year fixed mortgage rates from FRED and engineer price, time, and market-analysis features.
- Filter sold-price outliers and implausible close-to-original-list-price ratios.
- Explore leakage-aware sale-price models with linear regression, random forest, and XGBoost.

## Data Flow

```text
Trestle API or monthly CRMLS CSVs
              |
              v
data/raw -> data/processed -> data/filtered -> data/mortgage
                                                    |
                                                    v
data/cleaned -> data/feature_engineer -> data/post_outlier
                                                    |
                                                    v
                                    Tableau + modeling notebooks
```

## Project Structure

```text
idx/
├── data/                              # Local-only inputs, reference data, and outputs
│   ├── raw/                           # Monthly CRMLS listing and sold exports
│   ├── processed/                     # Combined residential datasets
│   ├── filtered/                      # Datasets after missing-column filtering
│   ├── mortgage/                      # Datasets enriched with FRED mortgage rates
│   ├── cleaned/                       # Cleaned listing and sold datasets
│   ├── feature_engineer/              # Feature-engineered sold dataset
│   ├── post_outlier/                  # Final outlier-filtered sold dataset
│   ├── city_boundaries/               # California city/county boundary GeoJSON
│   └── zip/                           # Valid California ZIP-code reference
├── notebooks/
│   ├── clean.ipynb                    # Cleaning exploration and row-count review
│   ├── feature_engineer.ipynb         # Feature exploration and grouped summaries
│   ├── outlier.ipynb                  # Outlier and price-ratio investigation
│   └── modeling.ipynb                 # Sale-price modeling experiment
├── tests/
│   ├── test_clean.py                  # Geographic flagging tests
│   ├── test_extract_crmls.py          # Extraction, retry, and validation tests
│   ├── test_pipeline.py               # Pipeline argument and stage-order tests
│   └── test_process.py                # Monthly discovery and combination tests
├── extract_crmls.py                   # Monthly Trestle extraction
├── process.py                         # Monthly-file discovery and aggregation
├── validation.py                      # Missingness analysis and column filtering
├── mortgage_fetch.py                  # FRED mortgage-rate enrichment
├── clean.py                           # Reusable cleaning and geographic checks
├── feature_engineer.py                # Sold-record feature engineering
├── outlier.py                         # Sold-record outlier filtering
├── pipeline.py                        # End-to-end pipeline runner
└── requirements.txt                   # Pinned core Python dependencies
```

## Setup

The current environment uses Python 3.13. Create a virtual environment and install the core dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The core stack is pandas, NumPy, GeoPandas, Shapely, Matplotlib, Statsmodels, and Requests. The installed requirements also include an IPython kernel plus SciPy, scikit-learn, and XGBoost for the modeling notebook.

Because `data/` is not committed, a new local setup must provide these reference files before running the full pipeline:

- `data/zip/california_valid_zip_codes.csv`, with a `ZIP_CODE` column
- `data/city_boundaries/City_and_County_Boundaries.geojson`, with a `COUNTY_NAME` field and polygon geometry

The stage directories under `data/` must also exist. Raw MLS data can be supplied as local monthly file pairs or fetched with the extractor.

## Fetching Monthly CRMLS Data

The extractor obtains a short-lived Trestle access token from the team authentication proxy. Create a local `.env` file with the two team-provided HTTPS endpoints:

```dotenv
CORELOGIC_API_URL=https://replace-with-team-api-url
AUTH_ENDPOINT=https://replace-with-team-auth-endpoint
```

Shell environment values override `.env`. Do not place endpoint values, access tokens, or MLS records in source files, notebooks, command-line arguments, screenshots, or logs.

Fetch an inclusive month range:

```bash
python extract_crmls.py --start-month 2026-08 --end-month 2026-08
```

Ranges may cross calendar years. Each month produces:

```text
data/raw/CRMLSListingYYYYMM.csv
data/raw/CRMLSSoldYYYYMM.csv
```

Existing files are skipped, which makes a long backfill resumable. Use `--force` to refresh them. A forced export writes to a temporary file and replaces the previous CSV only after the new download passes validation.

## Running the Pipeline

Run the transformations against monthly CSVs already in `data/raw/`:

```bash
python pipeline.py
```

Fetch a month range first and then run every transformation stage:

```bash
python pipeline.py --fetch-start 2026-08 --fetch-end 2026-08
```

Add `--force-fetch` to refresh existing monthly exports. Both fetch dates are required together, and the end month cannot be earlier than the start month.

`process.py` requires a listing and sold file for every discovered month and fails clearly when a pair is incomplete. When both `CRMLSSoldYYYYMM.csv` and `CRMLSSoldYYYYMM_filled.csv` exist, the `_filled` file is used.

The legacy `--with-reports` option still references `distribution.py`, which is not included in the current checkout. Run the pipeline without that flag unless the report script is restored.

## Transformation Details

| Stage | Script | Work performed | Main output |
| --- | --- | --- | --- |
| Extract | `extract_crmls.py` | Authenticates, checks the Trestle schema, follows pagination, validates records, and writes monthly exports. | `data/raw/CRMLSListingYYYYMM.csv`, `data/raw/CRMLSSoldYYYYMM.csv` |
| Process | `process.py` | Discovers complete month pairs, prefers filled sold files, combines all months, and keeps `PropertyType == "Residential"`. | `data/processed/CRMLSListing.csv`, `data/processed/CRMLSSold.csv` |
| Validate | `validation.py` | Profiles missingness and key sold distributions, then removes columns with more than 90% missing values. | `data/filtered/CRMLSListing_filtered.csv`, `data/filtered/CRMLSSold_filtered.csv` |
| Enrich | `mortgage_fetch.py` | Converts weekly FRED `MORTGAGE30US` observations to monthly averages and joins them by listing or close month. | `data/mortgage/*_with_mortgage.csv` |
| Clean | `clean.py` | Parses dates, flags timeline and numeric issues, normalizes names, filters state/ZIP values, checks coordinates against county polygons, removes redundant fields, and applies known data corrections. | `data/cleaned/CRMLSListing_cleaned.csv`, `data/cleaned/CRMLSSold_cleaned.csv` |
| Engineer | `feature_engineer.py` | Adds price ratios, price per square foot, close year/month, year-month labels, and listing-to-contract and contract-to-close durations. | `data/feature_engineer/CRMLSSold_feature_engineered.csv` |
| Filter | `outlier.py` | Applies a three-IQR `ClosePrice` boundary and keeps close-to-original-list ratios from 0.75 through 1.50. | `data/post_outlier/CRMLSSold_cleaned_out.csv` |

## Analysis Work Completed

- `feature_engineer.ipynb` explores key distributions and summarizes market measures by property subtype, county, MLS area, listing office, and buyer office.
- `outlier.ipynb` documents the investigation of extreme prices, source-data corrections, and alternative price-ratio boundaries.
- `modeling.ipynb` uses an 80/20 train/test split, five-fold cross-validation, categorical one-hot encoding, and a log-transformed target to compare linear regression, random forest, and XGBoost approaches.
- To reduce target leakage in modeling, the notebook replaces the close-month mortgage join with the most recent available weekly FRED rate strictly before the listing-contract date.
- Tableau work communicates statewide market trends and brokerage competitive analysis.

## Tests

Run the automated test suite with:

```bash
python -m unittest discover -s tests -v
```

The tests cover extraction retries and token refresh, safe pagination, schema and record validation, resumable/atomic exports, month-pair discovery, residential filtering, pipeline arguments, and county-coordinate matching.

### Tableau Visualizations
- Market Analysis: https://public.tableau.com/views/CaliforniaRealEstateMarketAnalysis_17882190871160/MarketAnalysis?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link
- Competitive Analysis: https://public.tableau.com/views/CaliforniaRealEstateCompetitiveAnalysis_17882211560250/CompetitiveAnalysisDashboard?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link
