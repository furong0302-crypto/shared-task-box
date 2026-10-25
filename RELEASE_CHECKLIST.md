# Pre-release checklist

GitHub source publication is authorized. PyPI publication remains intentionally separate.

## Required before a public release

- [x] Final project name chosen: 共享任务箱 (`shared-task-box`).
- [x] License chosen: MIT; `LICENSE` added.
- [ ] Replace the placeholder security-reporting instructions with a maintainer contact/process.
- [ ] Re-run the full test suite on Linux, macOS, and Windows if cross-platform support will be claimed.
- [ ] Decide whether claim leases/recovery belong in v1 or remain an embedding-host concern.
- [ ] Decide whether notification delivery needs a durable outbox; callbacks are currently best-effort.
- [ ] Decide the supported Python floor and verify it in CI.
- [x] Run privacy scan after Git initialization; repository history currently contains only reviewed release commits.
- [ ] Verify package metadata, classifiers, README rendering, and wheel/sdist contents.
- [ ] Review dependency/license compatibility if optional adapters gain third-party dependencies.
- [ ] Re-check nearby projects and wording immediately before publication; do not claim novelty.
- [x] Remote public GitHub repository created after explicit authorization.
- [x] GitHub Release authorized; PyPI package publication remains separate and is not performed.

## Candidate checks already completed

- [x] Core has no runtime dependencies outside Python standard library.
- [x] Candidate is isolated from the host application's source and database.
- [x] Duplicate event-id, concurrent claim, illegal transitions, cancellation, terminal writes, message cursor, redaction, notification minimization, CLI, and full-loop tests exist.
- [x] Remote repository creation occurred only after explicit publication authorization.
- [x] Git push is now authorized and performed; PyPI publication has not been performed.
