# Security model (zero-knowledge)

**End-to-end encryption** and **zero-knowledge** on the sync path: the server stores only ciphertext and cannot derive your vault master password.

## Threat model (summary)

| Actor | Can see plaintext SSH passwords / keys? |
|-------|----------------------------------------|
| termsh app (unlocked vault) | Yes — by design, on your device |
| termsh sync server | **No** — only opaque blobs |
| Server operator (you / us) | **No** — without your vault master password |
| Network attacker (TLS) | **No** — ciphertext only |
| Attacker with stolen JWT | Can download blobs — **cannot decrypt** |

Sync **account password** (API login) ≠ **vault master password**. The API password only obtains a JWT; it cannot decrypt sync blobs.

Optional **TOTP 2FA** on sync account (`POST /auth/totp/*`). Rate limits on auth endpoints.

## Local vault (at rest)

```
Master password (device only)
    └── Argon2id (19 456 KiB, t=2, p=1) ──► Master key (32 bytes, zeroized on lock)
                        └── AES-256-GCM ──► vault-data.enc.json (Electron)
                        └── AES-256-GCM ──► vault_records._bundle (termsh-core)
```

When **locked**, disk contains only salt + verifier + opaque encrypted bundle.

## Cloud sync (zero-knowledge)

Client encrypts full `SyncPayload` (type, ref, data) into one `encrypted_blob`.  
Server API: `POST /sync/blobs` — fields: `record_id`, `encrypted_blob`, `version` only.

## What is NOT zero-knowledge

- **SSH sessions**: plaintext in memory during active connection.
- **Vault unlocked + malware on device**: memory and clipboard are in scope.

Report: [SECURITY.md](SECURITY.md)
