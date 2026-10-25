# Security policy

## Trust model

共享任务箱 is a local persistence and coordination library. It does not authenticate callers and does not sandbox worker execution. Deploy it behind the embedding application's trust boundary or add an authenticated transport layer.

## Data minimization

The library has no chat-history discovery feature. Only explicitly submitted task content is stored. Default notifications include task metadata only and exclude bodies, context, results, and message text.

## Sensitive data

Public reads redact common credential-like patterns and structured sensitive keys. Redaction is defense-in-depth, not a secure secret store. Avoid submitting credentials to task content. Protect the SQLite file with normal operating-system permissions and storage controls appropriate to the host.

## Reporting

Use the repository's **Security** tab and private vulnerability reporting / Security Advisories when available. Do not put live credentials, exploit details, or sensitive reports in public issues, logs, examples, or test fixtures. If private reporting is unavailable, open a minimal public issue asking the maintainer for a private contact without including vulnerability details.
