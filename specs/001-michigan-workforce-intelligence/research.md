# Research Notes - Initial Source Strategy

Research captured 2026-09-11 from primary agency documentation.

- Michigan MCDA LAUS: monthly labor force/employment/unemployment estimates by residence. Do not equate people with payroll jobs.
- Michigan MCDA QCEW: employer/UI-based quarterly employment and wage data by industry.
- Michigan MCDA OEWS: annual occupational employment/wage estimates; Michigan explicitly warns that OEWS snapshots are not a normal year-to-year time series.
- Michigan MCDA Employment Projections: current statewide and Prosperity Region long-term projections include 2024-2034 industry and occupation workbooks.
- CEPI/MI School Data: Michigan's official public education-data portal; downloadable aggregate information includes postsecondary/workforce views.
- CEPI STARR: public universities/community colleges submit student academic records covering awards, programs, and courses; aggregate reporting feeds MI School Data.
- Michigan WLDS: links workforce and educational data for aggregate outcome/ROI analysis.
- BLS Public Data API v2: REST time-series interface; registered access expands limits/features.
- Census QWI: workforce indicators including employment, job creation/destruction, wages and hires across geography/industry/worker characteristics; current Census documentation requires API keys for queries.
- NCES IPEDS: downloadable enrollment, completions, awards, graduation and institution data; complete/custom files are available historically.
- O*NET: occupational tasks, skills, knowledge, abilities, technology and related descriptors; bulk database and web-service access are available.
- Apprenticeship.gov: RAPIDS-based state/national registered apprenticeship dashboards and public statistics.

The source registry stores these as source families rather than assuming every portal exposes a stable API. Downloaded XLSX/CSV/JSON/PDF artifacts are first-class immutable evidence.
