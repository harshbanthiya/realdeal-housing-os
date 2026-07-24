-- 070: drive catalog — an index of what actually exists on the RDH 5TB drive.
--
-- The drive is the real corpus: ~45k files of footage, brochures, owner/broker/
-- tenant sheets, IGR captures and PC backups. Only "RDH ALL Footage" was ever
-- catalogued (media_assets, 5,885 rows), so every other question — "do we have
-- a brochure for Oberoi Esquire?", "where are the tenant sheets?" — needed a
-- manual find. This table answers those from SQL.
--
-- Deliberately NOT a vector store: path + filename + extension already carry
-- almost all the signal (the folder tree IS the taxonomy here). Content
-- extraction/embeddings only become worth it once we're asking questions that
-- filenames can't answer — see docs/DRIVE-MAP.md "when to upgrade".

CREATE TABLE IF NOT EXISTS drive_files (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path        text NOT NULL UNIQUE,
  file_name        text NOT NULL,
  parent_dir       text NOT NULL,
  top_area         text NOT NULL,          -- 'RDH DATA 2024/RDH', 'PT', …
  file_ext         text,
  file_size_bytes  bigint,
  modified_at      timestamptz,

  -- inferred, cheap, and always re-derivable from the path (see scanner)
  building_id      uuid REFERENCES buildings(id),
  building_guess   text,                   -- matched alias, kept for auditing
  doc_kind         text,                   -- brochure | owner_sheet | broker_sheet | …
  content_class    text,                   -- document | spreadsheet | video | image | …
  confidence       text,                   -- high | medium | low
  is_noise         boolean NOT NULL DEFAULT false,  -- plist/code/system junk

  first_seen_at    timestamptz NOT NULL DEFAULT now(),
  last_seen_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS drive_files_building_idx  ON drive_files (building_id) WHERE building_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS drive_files_kind_idx      ON drive_files (doc_kind) WHERE doc_kind IS NOT NULL;
CREATE INDEX IF NOT EXISTS drive_files_class_idx     ON drive_files (content_class);
CREATE INDEX IF NOT EXISTS drive_files_area_idx      ON drive_files (top_area);
CREATE INDEX IF NOT EXISTS drive_files_name_trgm_idx ON drive_files USING gin (file_name gin_trgm_ops);

COMMENT ON TABLE drive_files IS
  'Catalog of the RDH 5TB drive. Rebuilt by scripts/scan_drive_catalog.py; '
  'inference is path-based and re-derivable, so it is safe to re-scan at will.';

-- What we have per building, at a glance — the answer to "what can I work with?"
CREATE OR REPLACE VIEW vw_drive_building_coverage AS
SELECT
  b.id   AS building_id,
  b.name AS building_name,
  count(*)                                                    AS files,
  count(*) FILTER (WHERE d.doc_kind = 'brochure')             AS brochures,
  count(*) FILTER (WHERE d.doc_kind = 'owner_sheet')          AS owner_sheets,
  count(*) FILTER (WHERE d.doc_kind = 'broker_sheet')         AS broker_sheets,
  count(*) FILTER (WHERE d.doc_kind = 'tenant_sheet')         AS tenant_sheets,
  count(*) FILTER (WHERE d.doc_kind = 'igr_document')         AS igr_docs,
  count(*) FILTER (WHERE d.doc_kind = 'rera_document')        AS rera_docs,
  count(*) FILTER (WHERE d.doc_kind = 'agreement')            AS agreements,
  count(*) FILTER (WHERE d.content_class = 'video')           AS videos,
  count(*) FILTER (WHERE d.content_class = 'image')           AS images,
  count(*) FILTER (WHERE d.content_class = 'spreadsheet')     AS spreadsheets,
  pg_size_pretty(sum(d.file_size_bytes))                      AS total_size
FROM buildings b
LEFT JOIN drive_files d ON d.building_id = b.id AND d.is_noise IS FALSE
GROUP BY b.id, b.name;

-- Unattributed business files: the working queue for "who does this belong to?"
CREATE OR REPLACE VIEW vw_drive_unattributed AS
SELECT top_area, doc_kind, content_class, count(*) AS files,
       pg_size_pretty(sum(file_size_bytes)) AS size
FROM drive_files
WHERE building_id IS NULL AND is_noise IS FALSE
  AND content_class IN ('spreadsheet', 'document', 'video')
GROUP BY 1, 2, 3
ORDER BY 4 DESC;
