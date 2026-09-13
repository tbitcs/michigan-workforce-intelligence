# Data credits and third-party notices

[![O*NET OnLine](docs/assets/onet-online.png)](https://www.onetonline.org/)

**O*NET credit:** This project uses O*NET OnLine material from the National Center for O*NET Development and the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). O*NET® is a USDOL/ETA trademark. We selected wage benchmarks and added comparisons, interpretation and proposed pathways. Those modifications have not been approved, tested or endorsed by USDOL/ETA. Wage pages identify BLS as the underlying wage-data source. [OnLine license](https://www.onetonline.org/help/license), [database license](https://www.onetcenter.org/license_db.html), [authorized graphics](https://www.onetcenter.org/graphics.html).

The supplied O*NET graphic is unmodified and displayed proportionally as a source credit, not as project branding or an endorsement. Its archive/member provenance is in [graphic metadata](docs/assets/onet-credit.json). No O*NET Web Services API is called by this implementation; enabling it requires the separate service terms and prominent service attribution. Database-release attribution must identify the actual release when database content is ingested; this report's wage extracts came from OnLine and are not asserted to be an ingested O*NET 31.0 database.

| Provider | Material used or cataloged | Required handling in this project |
|---|---|---|
| U.S. Bureau of Labor Statistics | LAUS, CPS, CES, CPI, QCEW; BED/JOLTS/OEWS discovery | Credit BLS/program, series/release, geography, period and revisions. Clearly identify project calculations. [BLS copyright](https://www.bls.gov/bls/linksite.htm) |
| U.S. Census Bureau / LEHD | ACS, QWI, LODES/PSEO coverage and discovery | Credit product, vintage, geography, uncertainty/suppression and source. Never redistribute restricted microdata or infer individuals. [Census policies](https://www.census.gov/about/policies.html) |
| U.S. Bureau of Economic Analysis | SARPP price-parity history and regional-account discovery | Credit BEA, table/line, year and release; price parity is not household costs. [BEA policies](https://www.bea.gov/about/policies-and-information) |
| NCES / U.S. Department of Education | IPEDS, CIP-SOC crosswalk, College Scorecard | Credit component/year/cohort and preserve disclosure flags. Crosswalk links are not placements. |
| Michigan MCDA / LEO / UIA / MiLEAP / MEDC | Labor releases, projections and program eligibility | Cite the original dated page/document. Use factual summaries, not wholesale copying. Agency seals and third-party material are not relicensed. |
| U.S. DOL / Job Corps / apprenticeship offices | Program/eligibility descriptions and outcome-report inventory | Credit original program pages; advertised intake is not guaranteed capacity. |
| Federal Reserve Board / New York Fed | Economic and expectation reports/catalog | Credit original Reserve source and release; expectations are survey responses. Check provider reuse terms before bulk redistribution; no unrestricted republication of third-party series assumed. |
| HUD / EIA | Candidate housing/energy data | Catalog only until endpoint credentials and current terms are configured/reviewed. |
| Colleges, APEX partners and Velocity | Their own descriptions of services/programs | Short attributed factual summaries only; candidate participation and grant availability unconfirmed. |

The repository's original-code license does **not** relicense external datasets, graphics, trademarks, publications or dependency code. A public government host can contain third-party licensed content. Michigan job-ad analyses may use commercial inputs; this project does not redistribute underlying Lightcast/HWOL data. University of Michigan consumer sentiment, private confidence indexes and market-price feeds require their own access/reuse review; they are not silently copied from an aggregator such as FRED.

Prominent source notices appear in the README and PDF opening credits, and each table/chart identifies its source and transformations. Follow [API/source policy](docs/source-policy.md) before adding an automated source. The project makes no claim that a provider endorses the analysis or pilot.
