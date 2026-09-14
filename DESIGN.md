---
name: California Housing Market Analysis
description: A map-led analytical workspace for California housing markets.
colors:
  navy: "#23496b"
  ink: "#233d52"
  muted: "#536a7d"
  page: "#f5f7f9"
  surface: "#fff"
  border: "#dbe3ea"
  map-field: "#edf3f6"
  focus: "#bd632c"
  selected: "#e8eff4"
  hover: "#edf2f6"
  price: "#c26d35"
  sales: "#258187"
  listings: "#548751"
  rate-agent: "#4778aa"
  price-area: "#9a775e"
  days: "#bc5663"
  ratio-office: "#916695"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "24px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-.025em"
  section:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "19px"
    fontWeight: 650
    lineHeight: 1.5
    letterSpacing: "-.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-.015em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.5
  metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "25px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-.025em"
  metric-primary:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "43px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-.035em"
rounded:
  field: "5px"
  button: "6px"
  chart: "10px"
  overview: "12px"
spacing:
  compact: "6px"
  small: "8px"
  control: "12px"
  medium: "16px"
  panel: "20px"
  overview: "24px"
  page: "28px"
components:
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "8px 12px"
  button-default-hover:
    backgroundColor: "{colors.hover}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.button}"
    padding: "8px 12px"
    height: "38px"
  field-select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "7px 28px 7px 10px"
  segmented-selected:
    backgroundColor: "{colors.selected}"
    textColor: "#183e5e"
    padding: "7px 11px"
  analysis-tab:
    backgroundColor: "transparent"
    textColor: "{colors.navy}"
    padding: "14px 0"
  chart-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.chart}"
  area-summary:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.overview}"
    padding: "24px 25px 18px"
  map-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.overview}"
---
# Design System: California Housing Market Analysis

## Overview

**Creative North Star: "California in Focus"**

California in Focus is a calm analytical workspace: navy identity frames real geography, and crisp white surfaces keep numbers and comparisons legible. The map and selected-area summary form a coupled overview; analysis continues below without losing the selected market.

The visual language is compact, practical and restrained. System sans typography and tabular numerals are confirmed project choices. Color earns its place through identity, selection, focus or a stable data-series role; the interface carries no marketing content.

**Key Characteristics:**
- Navy identity with cool pale geography and white analytical surfaces.
- Compact system typography with aligned tabular numerals.
- Fine blue-gray boundaries and flat, gently rounded containers.
- Consistent series colors, visible focus and table alternatives.

## Colors

A deep navy anchor sits among cool neutral surfaces; a restrained analytical palette distinguishes measures and entities. The frontmatter owns canonical values.

### Primary
- **Market Navy** (`navy`): masthead, active analysis tab, primary metric and darkest choropleth stop.
- **Focus Copper** (`focus`): keyboard focus outline, distinct from the price-series orange.

### Secondary
- **Price Orange** (`price`) and **Sales Teal** (`sales`): median-price and closed-sales series; closed sales also uses a dashed line in the paired activity chart.
- **Listings Green** (`listings`): incoming supply.
- **Rate and Agent Blue** (`rate-agent`): national mortgage rates and agent rankings in their respective contexts.
- **Price-Area Brown** (`price-area`), **Days Rose** (`days`), and **Ratio and Office Plum** (`ratio-office`): price per square foot, days on market, and ratio or brokerage analysis respectively.

### Neutral
- **Slate Ink** (`ink`) and **Muted Slate** (`muted`): primary and secondary interface text.
- **Cool Page** (`page`), **White Surface** (`surface`), and **Map Mist** (`map-field`): page canvas, analytical containers and map ground.
- **Blue-gray Rule** (`border`): panel and control boundaries. **Selected Wash** (`selected`) and **Hover Wash** (`hover`) distinguish control states.

**The Identity and Evidence Rule.** Use navy for identity and selection; reserve the chart palette for stable metric and entity meanings.

## Typography

**Headline and Body Font:** the system sans stack in the frontmatter. This is an explicit project commitment, including the masthead; no decorative display family is introduced.

**Character:** compact, clear and analytical. Tabular numerals support comparison. The primary metric carries the strongest scale contrast; headings stay subordinate to the data.

### Hierarchy
- **Headline:** masthead identity; reduces to (19px) at the mobile breakpoint and (18px) on the narrowest layout.
- **Section:** main analytical sections; map-panel heading uses (17px).
- **Title:** chart titles.
- **Body:** controls, methodology and compact explanatory content; supporting descriptions commonly use (12px).
- **Label:** filter labels and table headings, sentence case.
- **Metric:** supporting summary values; the selected-area title uses (24px, weight 600).
- **Primary metric:** median close price; mobile styles use a compact summary, with the final cascade rendering all summary values at (26px) below the mobile breakpoint. Treat the desktop primary-metric role as desktop only.

**The Numeric Rhythm Rule.** Keep tabular numerals and explicit units across summaries, axes and tables.

## Layout

The desktop content container is centered with a maximum width of (1566px) and horizontal padding of (28px). The masthead aligns with that content. A single filter toolbar precedes the overview. The overview uses a (2.1fr / 1fr) grid, a minimum summary width of (295px), and a (24px) gap. Trends and competition use a two-column chart grid with (20px) gaps. A tall paired price/rate panel spans two chart rows.

At (1150px) and below, the overview changes to (1.8fr / 1fr) with a (16px) gap and a (280px) minimum summary. Controls wrap and summary spacing tightens. At (800px) and below, the overview and charts become one column, content padding becomes (18px), geography/property filters live in a toggleable two-column grid, and reporting month remains exposed. Map controls wrap without narrowing the metric selector below (178px). At (430px) and below, page padding becomes (12px), and the map heading and controls stack.

The map height is (428px) normally, (480px) from (1600px), (440px) at the mobile breakpoint, and (390px) on the narrowest layout. Standard charts are (218px), expanding to (250px) on wide screens and (225px) on mobile. The paired price/rate chart has a minimum height of (505px). Tables scroll horizontally within their containers; numerical columns align right, names align left.

## Elevation & Depth

The system is flat. White containers and cool backgrounds establish layers through fine borders, not drop shadows. Map controls explicitly remove the library's default shadow. Hover uses a pale fill; keyboard focus uses a copper outline (3px) offset by (3px). Overlaid map tooltips remain white, bordered and compact.

**The Flat Surface Rule.** Use subtle borders and tonal separation to establish panels; do not add ornamental shadows.

## Shapes

Small controls have lightly rounded corners: field and segmented-group radii use `field`, ordinary buttons use `button`, chart and ranking containers use `chart`, and overview containers use `overview`. Borders are generally (1px). Segmented controls share one outer boundary, with square internal joins. Analysis tabs are flat text controls with a selected underline (3px). Chart lines use (2.5px) strokes and restrained area fills (opacity 0.06).

## Components

### Buttons
Compact, quiet controls. The default button is white with a fine border and the `button-default` padding. Hover applies `button-default-hover`. Ghost reset controls have no border. Disabled buttons use opacity (0.4) and a default cursor. Background and text transitions last (160ms); reduced motion disables transitions. There is no incumbent filled primary-button variant.

### Inputs / Fields
Native selects are the implemented field primitive. They use a blue-gray stroke, white background, compact system text (13px), and minimum height (38px). Map selectors use (12px) text and a smaller desktop minimum height (33px). They inherit the shared focus outline. No text-input or error-field variant exists yet.

### Chips
No chip or tag primitive is implemented. Binary geography and time-range choices use segmented buttons instead: the selected item receives Selected Wash and darker navy text, with `aria-pressed` carrying the state.

### Cards / Containers
Panels are white, bordered and gently rounded. Overview headings use (16px 20px) padding; the selected-area summary uses its frontmatter padding and a two-column metric grid. Chart headings use (19px 22px 12px). Panels are not clickable cards and receive no lift on hover.

### Navigation
Two analysis tabs share a bottom rule. The active tab gains navy text, a navy underline and stronger weight; inactive tabs remain muted. Arrow keys switch tabs and move focus. Small screens retain both tab labels and omit the redundant context at the far right.

### Geographic overview
The county/ZIP choropleth uses six incumbent stops from pale teal to navy. Selected boundaries use a dark outline (2.5px), while other boundaries are white. The legend distinguishes lower/higher values and unshaded missing data. Sales concentration uses a heatmap on a pale geography base. Reset-to-California travel lasts (450ms), becoming instant for reduced motion. No decorative map assets substitute for actual boundary geometry.

### Charts and tables
Stable series colors and explicit axis units carry analytical meaning. Prices and mortgage rates use separate aligned plots. Charts animate for (300ms) unless reduced motion is requested. Every chart includes a disclosure for its data table; map data is also available in a table. Ranking charts truncate long names while tables retain the full text. Export and pagination use the same quiet controls as the rest of the application.

## Do's and Don'ts

### Do:
- Do preserve the navy identity and confirmed system font stack.
- Do couple geographic selection to visible market context.
- Do retain explicit units, neutral month comparisons and table alternatives for every chart.
- Do keep keyboard focus visible and respect reduced motion.
- Do keep price and mortgage rate in aligned plots with separate labeled scales.

### Don't:
- Don't replace real geography with decorative imagery.
- Don't use metric colors as arbitrary interface accents.
- Don't introduce marketing content or decorative display typography.
- Don't hide selection state in color alone; preserve labels, pressed states and the active-tab underline.
- Don't force desktop columns onto narrow screens.
