# Postgres Storage Migration Plan (Phase 3.9B → executed 3.9C)

**Status: EXECUTED in Phase 3.9C on 2026-06-08.** Postgres now runs on the APFS
sparsebundle. The original exFAT `data/postgres` was **copied, not moved**, and is
preserved intact as the rollback source. See **Section 12 — Execution record (Phase 3.9C)**
for actual results and the verified rollback procedure.

This plan describes how to move the Postgres data directory off direct exFAT
storage before Phase 4, so the database stops depending on the fragile
AppleDouble cleanup/retry loop in `start.sh`.

---

## 1. Current problem summary

- The project runs from an **exFAT** external volume: `/Volumes/RDH 5TB` (`noowners`).
- Postgres data is **bind-mounted** from the repo:
  `../data/postgres` → `/var/lib/postgresql/data` (see `docker/docker-compose.yml`).
- macOS stores extended attributes on exFAT as AppleDouble `._*` sidecar files
  (one per real file). Docker's bind mount re-materialises thousands of these
  under `data/postgres` on every container bring-up.
- The Postgres entrypoint runs `find $PGDATA ! -user postgres -exec chown postgres`
  as root. On `noowners` exFAT the real files' chown is a harmless no-op, but it
  **fails on every `._*` file** ("Operation not permitted"), trips `set -e`, and
  the container exits → the stack reports `dependency postgres ... is unhealthy`.
- `start.sh` currently works around this with a preflight clean + a 3-attempt
  staged retry. It is reliable in practice but **fragile** (attempt 1 routinely
  fails and attempt 2 succeeds), and it depends on macOS host-side cleanup
  because the container itself cannot delete `._*` files.

Current measured state (for reference, see Phase 3.9B inspection):

| Item | Value |
|---|---|
| Postgres bind source | `/Volumes/RDH 5TB/Real Deal Housing OS/data/postgres` |
| `data/postgres` on-disk size | ~733 MB |
| Databases | `realdeal_os` (~11 MB), `realdeal_n8n` (~13 MB), `realdeal_nocodb` (~15 MB), `postgres` |
| Free space on drive | ~3.7 TiB |
| Spotlight on volume | disabled (`mdutil -i off` + `.metadata_never_index`) |

## 2. Why exFAT is unsafe for Postgres bind mounts on macOS

- **No POSIX ownership/permissions** (`noowners`): Postgres expects a data dir
  owned by the `postgres` user with mode `0700`. exFAT cannot represent this.
- **AppleDouble `._*` proliferation**: any xattr (quarantine, Finder, Spotlight,
  or a plain write) becomes a `._*` sidecar file. They regenerate on Docker
  bring-up and on any host write, and the container cannot delete them.
- **No journaling**: exFAT is not crash-consistent. A power loss or improper
  unmount can corrupt files mid-write — dangerous for a database's WAL/heap.
- **Case-insensitive, limited metadata**: not the environment Postgres assumes.

APFS (native macOS) solves all of these: real ownership/permissions, native
xattrs (no `._*` files), and a journaled, crash-consistent filesystem.

## 3. Recommended option

**Option B — APFS sparsebundle stored on the external drive, mounted as an APFS
volume, with Postgres data inside it.** (See Section 4 for full comparison and
Section 6 for steps.) It keeps the data **on the external drive** (preserving the
project's local-first / portable goal) while giving Postgres a real APFS
filesystem with no AppleDouble files. Verified feasible on this Mac
(macOS 26.5.1, `hdiutil` supports `-fs APFS -type SPARSEBUNDLE`, ample free space).

Fallback if Docker file-sharing of the mounted volume proves troublesome:
**Option A (Docker named volume)** — most bulletproof, but the data then lives in
the Docker Desktop VM (internal disk), reducing external-drive portability.

## 4. Alternative options (comparison)

| Option | Reliability | Portable w/ drive | Setup effort | Main drawback |
|---|---|---|---|---|
| **A. Docker named volume** | Highest | No (lives in Docker VM) | Low | Data leaves the external drive; tied to this Mac's Docker |
| **B. APFS sparsebundle on drive (recommended)** | High | Yes | Medium | Must mount image before startup; sparsebundle-on-exFAT needs clean unmounts |
| **C. APFS-formatted partition/drive** | Highest (native) | Yes | High / invasive | Requires repartitioning (destructive) or a second drive |
| **D. Stay on exFAT + cleanup retry (current)** | Fragile | Yes | None | Flaky startup; not acceptable long-term before Phase 4 |

## 5. Backup plan before migration (do this first, always)

Take **two independent backups** while the stack is healthy:

1. **Logical dump** (portable, restorable into any Postgres 16):
   ```bash
   ./scripts/backup_postgres_before_migration.sh            # dry run (default): shows what/where
   ./scripts/backup_postgres_before_migration.sh --apply    # writes pg_dumpall to backups/ (when approved)
   ```
   Output: `backups/postgres_pre_migration_<timestamp>/all_databases.sql` (git-ignored).

2. **Cold filesystem copy** of the stopped data dir (binary-exact fallback):
   ```bash
   ./stop.sh
   ./scripts/clean_appledouble_junk.sh --apply
   ditto 'data/postgres' 'backups/postgres_datadir_copy_<timestamp>'
   ```

Keep both until the migrated setup has been verified over several sessions.

## 6. Exact migration steps (NOT executed)

> Run only after explicit approval. Steps assume Spotlight already disabled on the volume.

```bash
# 0. Backups first (Section 5). Stack should be healthy before dumping.

# 1. Create an APFS sparsebundle on the external drive (sparse: grows as needed).
hdiutil create -size 50g -fs APFS -type SPARSEBUNDLE \
  -volname RDH_POSTGRES_DATA \
  '/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'

# 2. Mount it (mounts at /Volumes/RDH_POSTGRES_DATA).
hdiutil attach '/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'
mkdir -p /Volumes/RDH_POSTGRES_DATA/postgres

# 3. Stop the stack for a consistent cold copy.
./stop.sh
./scripts/clean_appledouble_junk.sh --apply     # don't copy junk into APFS

# 4. COPY (do not move) the data dir into the APFS volume.
ditto 'data/postgres/' '/Volumes/RDH_POSTGRES_DATA/postgres/'

# 5. Ensure Docker Desktop file sharing includes /Volumes/RDH_POSTGRES_DATA
#    (Docker Desktop > Settings > Resources > File Sharing). Add it if missing.

# 6. Point compose at the new path (Section 9), then start and verify (Section 8).
./start.sh
docker ps
./scripts/check_db.sh
```

The original `data/postgres` is **left untouched** as the rollback source until
the new setup is confirmed.

## 7. Rollback plan

Because step 4 **copies** rather than moves, the original data is always intact:

1. Revert `docker/docker-compose.yml` to the original bind mount
   (`../data/postgres:/var/lib/postgresql/data`).
2. Revert any `start.sh` changes.
3. `./start.sh && ./scripts/check_db.sh` — back on the original exFAT data dir.
4. Optionally `hdiutil detach /Volumes/RDH_POSTGRES_DATA` and delete the
   sparsebundle once you decide not to proceed.

If the database is damaged, restore from backup (Section 5): a cold copy restore
(replace data dir) or a logical restore (`psql -f all_databases.sql` into a fresh
cluster).

## 8. Verification checklist after migration

- [ ] `docker ps` shows `realdeal-postgres` healthy + `n8n`/`nocodb`/`adminer` up.
- [ ] `./scripts/check_db.sh` passes (20 tables + 12 views).
- [ ] Postgres data dir resolves to the APFS volume (`docker inspect` mount source).
- [ ] **No `._*` regenerate** inside the APFS postgres dir after a few start cycles.
- [ ] Business-data counts unchanged vs. pre-migration:
      canonical contacts = 0; `import_batches` = 2; `REAL_PHASE_3_5_TEST_001` exists;
      review statuses 40 pending / 3 approved / 2 needs_more_info; source-aware rows
      (source_files 1, contact_import_rows 22, contact_methods 62, lead_requirements 22,
      duplicate_candidates 1, import_review_items 45); canonical_merge_batches = 1.
- [ ] `start.sh` no longer needs the retry loop for Postgres (attempt 1 succeeds).

## 9. How to update docker-compose.yml / start.sh

**docker-compose.yml** — change the Postgres data volume:
```yaml
# before
      - ../data/postgres:/var/lib/postgresql/data
# after
      - /Volumes/RDH_POSTGRES_DATA/postgres:/var/lib/postgresql/data
```

**start.sh** — add a pre-start guard (critical safety):
- Before `docker compose up`, verify the sparsebundle is mounted; if not,
  `hdiutil attach` it.
- **Hard-abort if `/Volumes/RDH_POSTGRES_DATA/postgres` is missing or empty** —
  otherwise Docker may auto-create an empty bind dir and Postgres would
  initialise a brand-new empty cluster (looks like data loss).
- The AppleDouble preflight can stay (it still protects the rest of the tree),
  but the `data/postgres` guard becomes unnecessary for the live DB.

**stop.sh** — optionally `hdiutil detach /Volumes/RDH_POSTGRES_DATA` after
`docker compose down`, for a clean unmount.

## 10. Risks

- **Empty-mount data loss illusion**: if the image isn't mounted at start, Postgres
  may init a fresh empty cluster. → Mitigation: the start.sh mount + non-empty guard above.
- **Docker file sharing**: Docker Desktop must share `/Volumes/RDH_POSTGRES_DATA`.
  → Verify in Settings; fall back to Option A if VirtioFS won't follow the mount.
- **Sparsebundle-on-exFAT integrity**: improper unmount / power loss on the exFAT
  host can damage the bundle. → Clean unmounts, keep logical backups, consider Option C long-term.
- **Two stores at once**: never run Postgres against both old and new paths simultaneously.
- **Performance**: the disk-image layer adds minor overhead; negligible at this data size.

## 11. What NOT to do

- Do **not** delete or `rm` the original `data/postgres` until the migrated setup
  is verified across several sessions.
- Do **not** move (only copy) data in the first pass.
- Do **not** commit `docker/.env`, the sparsebundle, or anything under `backups/`,
  `data/`, `exports/`, `imports/` (all git-ignored).
- Do **not** run the migration without both backups in hand.
- Do **not** perform any of this until explicitly approved — this is a plan only.

## 12. Execution record (Phase 3.9C — 2026-06-08)

Executed with the stack healthy beforehand. No data was moved or deleted; the
copy was additive and the original exFAT data dir is untouched.

**What was done**
1. Captured pre-migration counts (all matched the Section 8 baseline).
2. Logical backup written (git-ignored):
   `backups/postgres_pre_migration_20260608_095758/all_databases.sql` (~772 KB).
3. Stopped the stack (`./stop.sh`); confirmed no `realdeal-*` containers remained.
4. Created APFS sparsebundle: `hdiutil create -type SPARSEBUNDLE -fs APFS -size 50g
   -volname RDH_POSTGRES_DATA '/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'`.
5. Mounted it (`hdiutil attach`) → `/Volumes/RDH_POSTGRES_DATA` (APFS, journaled,
   writable); created `/Volumes/RDH_POSTGRES_DATA/postgres`.
6. **Copied** (rsync `-a`, excluding `._*`/`.DS_Store`) from `data/postgres/` →
   `/Volumes/RDH_POSTGRES_DATA/postgres/`. Result: 3449 real files both sides,
   0 junk on target, ~93 MB logical, valid `PG_VERSION=16` cluster. Source preserved.
7. Pointed `docker/docker-compose.yml` Postgres volume at
   `/Volumes/RDH_POSTGRES_DATA/postgres:/var/lib/postgresql/data`.
8. Added `ensure_apfs_postgres()` guard to `start.sh`: mounts the sparsebundle if
   needed and **hard-aborts** before `docker compose up` if the APFS path is
   missing, empty, or lacks `PG_VERSION` (prevents an accidental empty-cluster init).
9. `./start.sh` → Postgres healthy on **attempt 1** (no retry needed); n8n, nocodb,
   adminer up; `check_db.sh` passes (20 tables + 12 views); 0 `._*` under the live
   APFS dir; mount source confirmed as the APFS path.
10. Post-migration counts identical to pre-migration (canonical contacts = 0;
    import_batches = 2; `REAL_PHASE_3_5_TEST_001` present; source_files 1,
    contact_import_rows 22, contact_methods 62, lead_requirements 22,
    import_review_items 45; review statuses 40 pending / 3 approved / 2
    needs_more_info; review_action_log 9; canonical_merge_batches = 1 rolled_back).

**Paths**
- Old (preserved rollback source): `/Volumes/RDH 5TB/Real Deal Housing OS/data/postgres` (733 MB, 3449 real files).
- New (live): `/Volumes/RDH_POSTGRES_DATA/postgres` (APFS sparsebundle at
  `/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle`).

**Rollback procedure (verified available; the original data is intact)**
```bash
cd '/Volumes/RDH 5TB/Real Deal Housing OS'
./stop.sh
# 1. Revert the compose Postgres volume back to the exFAT bind mount:
#    in docker/docker-compose.yml change
#      - /Volumes/RDH_POSTGRES_DATA/postgres:/var/lib/postgresql/data
#    back to
#      - ../data/postgres:/var/lib/postgresql/data
# 2. Revert start.sh (remove ensure_apfs_postgres call/guard) or simply use
#    `git checkout -- start.sh` if not yet committed.
./start.sh
./scripts/check_db.sh
# The original data/postgres is preserved and untouched, so this returns the
# stack to the pre-migration state. Optionally detach the image afterwards:
#   hdiutil detach /Volumes/RDH_POSTGRES_DATA
```
If the database itself is ever damaged, restore from the logical backup in
`backups/postgres_pre_migration_20260608_095758/all_databases.sql` into a fresh
cluster (`psql -f all_databases.sql`).

The original `data/postgres` should be retained until the APFS setup has been
verified across several sessions, then can be archived/removed in a later phase.
