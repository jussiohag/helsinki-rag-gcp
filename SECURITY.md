# Security Policy

## Reporting a Vulnerability

Use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on this repository.

## Supported Versions

Only the latest version on `main` receives security updates.

## Practices

- Commits scanned for secrets (gitleaks) and PII
- Dependencies monitored by Dependabot
- CI includes SAST (Semgrep) and dependency scanning (Trivy)
