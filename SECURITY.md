# Security Policy

## Supported versions

Only the latest commit on `main` is supported. Fixes are not backported to older
versions or tags.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub Security Advisories:
[Report a vulnerability](https://github.com/aimanmalib/contentforge/security/advisories/new)
(repository **Security** tab → **Report a vulnerability**).

Include what you found, steps to reproduce, and the impact you expect. You should
get an acknowledgement within a few days; once a fix is available we will credit
you in the advisory unless you prefer otherwise.

## Scope notes

- ContentForge sends your prompts and generated content to the LLM provider you
  configure. Treat that provider as a third party for any sensitive material.
- API keys are read from environment variables (or `${VAR}` references in the
  config file). `contentforge init` never writes a key to disk; avoid committing
  config files that contain literal keys.
