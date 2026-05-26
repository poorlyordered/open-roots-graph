# Security Policy

## Private Data

Genealogy exports can include sensitive information about living people and family relationships. Do not file public issues or pull requests containing real GEDCOM data, source notes, private locations, API keys, database dumps, or screenshots with sensitive records.

## Reporting

For now, report security issues privately to the repository maintainer after the public repository is created. Do not disclose vulnerabilities publicly until a fix is available.

## Secrets

Rotate any API key that was committed, pasted into an issue, or shared in logs. The project should run without `OPENROUTER_API_KEY`; that key only enables optional AI assistant features.

