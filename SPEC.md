# Weekly Report Specification

## Objective
Produce a high-signal weekly intelligence report covering:
1. Cancer research and care advances (clinical, translational, diagnostics, therapeutics, policy/regulatory)
2. Computational biology advances across domains (methods, AI/ML, single-cell, spatial, omics, genome editing)
3. Exceptional non-cancer medicine breakthroughs with outsized impact

## Audience
Computational biology PhD researcher with primary cancer focus.

## Time Window
- Weekly lookback: previous 7 days from run timestamp.
- Include only new or materially updated items in that window.

## Report Length
- Target: 15-minute read.
- Typical size: 1,800 to 2,600 words.

## Section Allocation
- Cancer: 50% of report body
- Computational biology: 35% of report body
- Exceptional non-cancer medicine: 15% of report body

## Prioritization
Use `config/scoring.yaml` to rank candidates and select only top items above thresholds.

## Conference Policy
Include conference-derived items only when they meet at least one:
- Late-breaking or plenary session with strong trial design
- Near-term practice-changing likelihood
- Regulator or guideline relevance

## Preprint Policy
Include preprints only when all are true:
- Composite score passes preprint threshold
- Methodology and effect size appear robust
- Broad downstream relevance is clear

## Required Report Structure
1. Executive summary (5 to 8 bullets)
2. Cancer (5 to 8 items)
3. Computational biology (4 to 6 items)
4. Exceptional medicine (1 to 3 items)
5. Watchlist (optional, at most 5 provisional items)
6. References (all primary links)

## Required Per-Item Template
- Headline
- One-sentence finding
- Why it matters (2 to 4 bullets)
- Evidence level (regulatory / phase III / phase II / observational / preprint)
- Caveats (1 to 3 bullets)
- Source links

## Source Registry
All routine source polling is defined in `config/sources.yaml`.

## Quality Checks Before Finalizing
- Every claim traceable to a cited source
- No duplicate developments
- No stale items outside the weekly window
- Explicit uncertainty labeling for preprints and early conference signals
- Section ratio close to 50/35/15
