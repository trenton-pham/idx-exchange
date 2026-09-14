# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Confirmed: React, TypeScript, Vite, MapLibre, ECharts; Python FastAPI, PostgreSQL, AWS Fargate and Lambda. Direct implementation without a generated mockup was selected.

## Users
People exploring California housing markets and listing-side agent and brokerage performance.

## Product Purpose
Replace the Tableau dashboard with an interactive, publicly accessible application backed by monthly CRMLS data. The user confirmed permission to display aggregates and named rankings.

## Capabilities and Constraints
Map beside selected-area summary, followed by Market Trends and Competitive Analysis tabs. Shared county/city/ZIP/subtype/month filters. Exact medians. Public responses contain aggregates only. Monthly refresh on day 7 at 06:00 America/Los_Angeles. RDS retains at most 36 completed reporting months; private S3 archives full history from January 2024. Existing Python cleaning and geographic improvements are preserved. Verified duplicate and invalid numeric defects are corrected and documented.

## Brand Commitments
California Housing Market Analysis; Overview by Trenton Pham. Preserve navy identity, improve border weight, typography, chart consistency and accessible contrast. Functional analytical interface with no marketing content.

## Evidence on Hand
Two supplied Tableau screenshots, existing Python pipeline and confidential local exports. Preview fixtures must be clearly labeled synthetic. No private source rows, credentials or addresses in source control or public responses.

## Accessibility & Inclusion
Keyboard controls, visible focus, accessible chart tables, reduced motion, responsive desktop/mobile layouts and WCAG AA contrast.
