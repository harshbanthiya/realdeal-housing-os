-- Phase 8.1: Contact groups for outreach (2 tables + 1 view).
--
-- Lets the cockpit build outreach audiences that are NOT tied to a building/owner
-- relationship: a 'test' group (for safe end-to-end testing) and operator-defined
-- 'custom' groups assembled by hand-picking contacts. The Lane A queue builder can
-- source from any group, with the SAME safety gates as the owner path (reachable
-- number, not suppressed / opted-out / in cooldown, send_enabled stays false).
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. contact_groups
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text NOT NULL UNIQUE,
  group_type text NOT NULL DEFAULT 'custom',     -- test, custom, system
  description text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_groups_type_check CHECK (group_type IN ('test','custom','system'))
);
CREATE INDEX IF NOT EXISTS idx_contact_groups_type ON contact_groups(group_type);

-- ---------------------------------------------------------------------------
-- 2. contact_group_members
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_group_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id uuid NOT NULL REFERENCES contact_groups(id) ON DELETE CASCADE,
  contact_id uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  added_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (group_id, contact_id)
);
CREATE INDEX IF NOT EXISTS idx_cgm_group_id ON contact_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_cgm_contact_id ON contact_group_members(contact_id);

-- ---------------------------------------------------------------------------
-- view: vw_contact_group_summary  (member counts + outreach reachability)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contact_group_summary AS
SELECT
  g.id::text AS group_id,
  g.slug,
  g.name,
  g.group_type,
  g.description,
  count(m.contact_id) AS member_count,
  count(m.contact_id) FILTER (
    WHERE EXISTS (SELECT 1 FROM contact_methods cm
                    WHERE cm.contact_id = m.contact_id
                      AND cm.method_type IN ('mobile','phone','whatsapp'))
  ) AS reachable_count,
  count(m.contact_id) FILTER (
    WHERE EXISTS (SELECT 1 FROM outreach_suppression_list s
                    WHERE s.contact_id = m.contact_id AND s.status = 'active')
  ) AS suppressed_count
FROM contact_groups g
LEFT JOIN contact_group_members m ON m.group_id = g.id
GROUP BY g.id, g.slug, g.name, g.group_type, g.description
ORDER BY g.group_type, g.name;
