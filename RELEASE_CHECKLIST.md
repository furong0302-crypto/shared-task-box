# Pre-release checklist

This candidate is intentionally not published yet.

## Required before a public release

- [x] Final project name chosen: 共享任务箱 (`shared-task-box`).
- [x] License chosen: MIT; `LICENSE` added.
- [ ] Replace the placeholder security-reporting instructions with a maintainer contact/process.
- [ ] Re-run the full test suite on Linux, macOS, and Windows if cross-platform support will be claimed.
- [ ] Decide whether claim leases/recovery belong in v1 or remain an embedding-host concern.
- [ ] Decide whether notification delivery needs a durable outbox; callbacks are currently best-effort.
- [ ] Decide the supported Python floor and verify it in CI.
- [ ] Run the privacy scan and a separate repository-history secret scan after Git initialization.
- [ ] Verify package metadata, classifiers, README rendering, and wheel/sdist contents.
- [ ] Review dependency/license compatibility if optional adapters gain third-party dependencies.
- [ ] Re-check nearby projects and wording immediately before publication; do not claim novelty.
- [ ] Create a remote repository only after explicit authorization.
- [ ] Publish a package only after explicit authorization.

## Candidate checks already completed

- [x] Core has no runtime dependencies outside Python standard library.
- [x] Candidate is isolated from the host application's source and database.
- [x] Duplicate event-id, concurrent claim, illegal transitions, cancellation, terminal writes, message cursor, redaction, notification minimization, CLI, and full-loop tests exist.
- [x] No remote repository was created.
- [x] No Git push or package publication was performed.
