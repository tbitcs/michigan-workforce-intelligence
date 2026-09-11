# Security and Data Handling

This baseline is designed for public aggregate workforce/education data. Do not ingest or commit PII, unemployment claimant records, protected student records, credentials, or licensed/restricted microdata without a separate security/privacy architecture review.

Secrets belong in environment variables. MCP mutation is disabled by default. Raw source artifacts are content-addressed and must remain immutable. Report any suspected ledger tampering, source substitution, or provenance break as an integrity incident.
