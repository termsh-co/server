# Security Policy

## Zero-knowledge & E2EE

termsh is designed so that **sync servers never receive plaintext secrets**. Vault master keys and SSH credentials stay on the client.

Details: [SECURITY_MODEL.md](SECURITY_MODEL.md)

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Older | No |

## Reporting a vulnerability

**Do not open public GitHub issues for security bugs.**

Email **termsh@monolitdigital.com** with:

- Description and impact
- Steps to reproduce
- Affected component (server / clients / ios / android / core)

We aim to acknowledge within **72 hours**.

## What we will never ask for

- Your vault master password
- SSH private keys or host passwords
- Production `JWT_SECRET`, database passwords, or API keys

## Scope

**In scope:** vault crypto, sync client/server, official apps under [termsh-co](https://github.com/termsh-co).

**Out of scope:** third-party VPS misconfiguration, leaked `.env` files, social engineering.
