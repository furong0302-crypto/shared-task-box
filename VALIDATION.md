# Candidate validation

Validation date: 2026-10-25.

## Functional tests

Command:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Result: **10 tests passed**.

Covered behavior:

- duplicate `event_id` replay;
- competing concurrent claims with exactly one winner;
- illegal state transitions;
- pending cancellation;
- terminal-state write rejection;
- `after_id` message cursors;
- structured and text credential redaction;
- notification payload minimization;
- full producer/worker loop;
- CLI round trip.

## End-to-end loop

`examples/full_loop.py` completed:

```text
create → claim → question → answer → progress → complete → result
```

The final status was `done` and the result was readable from the producer side.

## Standalone proof

The package was exercised in a clean environment whose Python path contained only this candidate package plus the standard environment. The flow completed without importing host-application source or locating a host database.

A wheel was also built from this directory, installed into a fresh virtual environment with no index access, and completed `create → claim → progress → complete` successfully.

## Privacy / secret scan

Command:

```bash
python scripts/privacy_scan.py .
```

Result: **clean**.

Additional candidate scans found no host-project name, production domain, production filesystem path, service ports, account identifiers, or production worker identifier. Test/example identities are generic placeholders.

## Host isolation check

Immediately before and after the final candidate test + example run:

- the serialized host task-list snapshot had the same SHA-256 hash;
- the host main database file had the same SHA-256 hash.

The candidate tests use only temporary/candidate SQLite databases. No host schema migration or deployment was performed.

## Publication state

- No Git repository was initialized in this candidate directory.
- No remote repository was created.
- Nothing was pushed.
- No package was published.
- Project name finalized as 共享任务箱 / `shared-task-box`.
- MIT License selected and `LICENSE` added.

See `RELEASE_CHECKLIST.md` for the remaining maintainer decisions.

## Name/license finalization check

After finalizing the name as **共享任务箱** (`shared-task-box`) and selecting **MIT**, the full 10-test suite, privacy scan, wheel build, fresh-venv install, and CLI startup were rerun successfully. No legacy candidate package name remains in source/docs/examples.
