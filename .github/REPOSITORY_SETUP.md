# Repository access and public downloads

The canonical repository is `tbitcs/michigan-workforce-intelligence`. The maintainer explicitly authorized public visibility on September 13, 2026, superseding the bootstrap's private-only setting.

Anyone may read, clone, fork, or download the public repository and its [report releases](https://github.com/tbitcs/michigan-workforce-intelligence/releases/latest). Only `tbitcs` has repository write access. Forks and proposed pull requests do not grant write access to this repository.

The active branch ruleset in `maintainer-branches.json` restricts creation, updates, deletion, and force pushes on every branch to its bypass actor, the repository administrator. This is a personal repository: `tbitcs` is its sole administrator. No collaborators, pending invitations, or deploy keys were present at the publication review. Adding credentials, apps, or collaborators later requires a fresh access review. CODEOWNERS documents review ownership; the GitHub ruleset and access permissions enforce it.

Actions default to read-only contents and cannot approve pull requests. The manually dispatched report publication job has scoped contents-write permission to create release tags and assets; it has no branch-rule bypass and cannot push branch commits. Tags remain available for timestamped report releases.

Public downloads contain reviewed aggregate evidence, reports, citations, charts, and reproducibility metadata. Local `.env` credentials, raw working volumes, confidential employer signals, and the employer exchange database are not published. Public source-code visibility does not expose or host the local Docker exchange.

Before publication, scan all Git history and the proposed release package for secrets and private data. Recheck collaborators, invitations, deploy keys, rulesets and workflow permissions after applying changes. Preserve this configuration with the GitHub API using the checked-in ruleset JSON; never put authentication values in commands or committed files.

Use `python scripts/repository_access.py` for a read-only access audit. After reviewing exposure, `--apply` reapplies public visibility, secret scanning, read-only workflow defaults and the checked-in branch ruleset; it fails if other writers, invitations or deploy keys need review.
