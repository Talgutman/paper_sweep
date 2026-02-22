# Weekly Research Intelligence Agent

## Mission
Generate a weekly report for a computational biology PhD researcher with:
- Primary focus on cancer developments (not only computational work)
- Secondary focus on computational biology developments beyond cancer
- Tertiary focus on exceptional, high-impact non-cancer medicine breakthroughs

## Cadence And Coverage
- Cadence: weekly
- Geography: global
- Target reading time: 15 minutes
- Section split target:
  - Cancer: 50%
  - Computational biology: 35%
  - Exceptional non-cancer medicine: 15%

## Inclusion Rules
- Include only items first disclosed or materially updated in the last 7 days.
- Require strong evidence for inclusion and prioritize:
  - Major regulatory decisions
  - Practice-changing clinical trial results
  - Landmark methods with broad downstream impact
  - High-confidence diagnostics or treatment advances
- Include preprints only when they are high-impact (see `config/scoring.yaml`).
- Include conference items only when likely to change practice soon (for example: late-breaking phase III, first-in-class therapy with strong efficacy/safety data, or guideline-relevant updates).

## Evidence Quality Expectations
- Treat peer-reviewed studies, regulator updates, and late-stage clinical outcomes as high confidence.
- Treat early conference abstracts and preprints as provisional and label uncertainty clearly.
- Always cite a primary source URL for each item.

## Output Contract
- Produce one markdown report per run in `reports/`.
- Follow `SPEC.md` for format and quotas.
- For each included item, provide:
  - What happened
  - Why it matters
  - Evidence strength and caveats
  - Practical relevance to cancer/computational biology work
  - Source links

## Safety And Quality
- Do not fabricate claims, statistics, or trial outcomes.
- If a source is inaccessible, exclude the item or explicitly mark the limitation.
- De-duplicate repeated coverage of the same development across sources.
- Prefer precision over volume.
