# Architecture Decision Records (ADRs)

This directory records the **significant architectural decisions** made on Voxa,
along with their context and consequences. An ADR captures *why* something is the
way it is — the reasoning a diagram or the code alone cannot convey.

We follow [Michael Nygard's format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions),
kept lightweight on purpose.

## Why we keep ADRs

- **Onboarding**: a new contributor (or a recruiter reading the repo) can understand
  the design rationale without archaeology through git history.
- **Avoiding re-litigation**: decisions already weighed are written down, with the
  alternatives we rejected and why.
- **Honest engineering**: every decision has trade-offs. ADRs make the negative
  consequences explicit, not just the wins.

## Conventions

- One decision per file, named `NNNN-short-title.md` (zero-padded, monotonically
  increasing).
- ADRs are **immutable once accepted**. We do not rewrite history: if a decision
  changes, add a new ADR and set the old one's status to `Superseded by ADR-XXXX`.
- Copy [`template.md`](template.md) to start a new one.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-product-name-and-scope.md) | Product name and scope: Voxa | Accepted |
| [0003](0003-english-as-canonical-project-language.md) | English as the canonical project language | Accepted |
| [0004](0004-layered-backend-architecture.md) | Layered backend architecture | Accepted |
| [0005](0005-camelcase-api-contract.md) | camelCase API contract with flattened errors | Accepted |
| [0006](0006-relative-api-paths-via-proxy.md) | Relative API paths via a reverse proxy | Accepted |
| [0007](0007-openai-for-ai-pipeline.md) | OpenAI for transcription and extraction | Accepted |
| [0008](0008-postgresql-asyncpg-sql-migrations.md) | PostgreSQL with asyncpg and SQL migrations | Accepted |
| [0009](0009-test-driven-development.md) | Test-driven development | Accepted |
| [0010](0010-containerized-delivery-docker-compose.md) | Containerized delivery with Docker Compose | Accepted |
| [0011](0011-secrets-and-configuration-management.md) | Secrets and configuration management | Accepted |
| [0012](0012-multi-language-strategy.md) | Multi-language strategy (end-to-end) | Proposed |
