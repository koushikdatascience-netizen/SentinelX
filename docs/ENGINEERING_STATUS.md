# Engineering review — October 27, 2026

## Completed in this review

- Prevented competing approval requests from overwriting a recorded decision using a conditional database update. Approval remains a decision with no external execution.
- Added a staging signup gate: public registration is off; only operator-approved emails can register. Empty allowlist closes signup. Existing accounts retain login. This does not verify email ownership.
- Validated UTF-8 password byte length before bcrypt, preventing server errors on long Unicode passwords.
- Updated stale README setup, capability claims and billing notes; clarified unverified owner-supplied evidence in the dashboard.
- Patched Next.js to 15.5.28 and pinned transitive security overrides for PostCSS 8.5.32 and sharp 0.35.5. Reassess/remove overrides when upgrading Next.js to a version that includes patched dependencies.
- Added frontend package-lock.json, reproducible CI/Docker installs and Docker build exclusions for local secrets, caches and databases.

## Local verification

- Backend: `..\.venv\Scripts\python.exe -m pytest -q` from backend — **39 passed**, with three dependency/startup deprecation warnings.
- Frontend: full `npm audit` — **0 vulnerabilities** at review time. This is a registry advisory check, not a security guarantee.
- Frontend: `npm run build` — **passed**, including TypeScript checks and static page generation, using patched dependencies.

Tests used local SQLite. PostgreSQL concurrency behavior and deployed browser behavior still require validation. This directory has no Git metadata, so no commit, push or remote CI result was produced.

## Still required

| Work | Dependency / completion evidence |
| --- | --- |
| Exact Meta API compatibility | Provider-supported schema, manual gated single-call workflow and sanitized result; credits alone do not verify access |
| Actual charge accounting and workspace quotas | Verified endpoint usage/pricing schemas, durable reservations and reconciliation tests |
| Real media and source-backed agent workflows | Consented fixtures, verified model access, source provenance and quality evaluations |
| Public crawler | Pinned DNS plus egress restrictions and adversarial SSRF tests; keep legacy routes disabled |
| Public service hardening | Durable auth rate limits, account recovery/revocation, email verification, migrations and tested backup/restore |
| Browser E2E and demo recording | Running stack, full account/workspace/audit/review/export journey and accurate simulation/inference labels |
| Hostinger CD and release | Add the restricted deployment account and GitHub Environment secrets, enable the protected workflow, verify first release and scheduled backups |

No paid request or external publishing was performed during this review. The current Hostinger staging audit and prepared CD workflow are recorded in [HOSTINGER_DEPLOYMENT.md](HOSTINGER_DEPLOYMENT.md). Kamal Woodcraft's main site and other Hostinger services remain outside deployment scope. Demo and paid-off defaults remain in place.
