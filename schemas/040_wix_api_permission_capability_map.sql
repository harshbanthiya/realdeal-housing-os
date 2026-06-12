-- Phase 7.21: Wix API permission / integration capability map.
--
-- A review-gated catalog that maps Wix API permissions to Real Deal Housing OS capabilities,
-- defines FUTURE API-key profiles, and queues human review BEFORE any key is created or used.
-- This schema stores NO secrets and NO API keys. It performs NO Wix API call, NO external API
-- call, NO publishing, NO live form/webhook, NO sends, and NO inbound-lead/contact writes. Key
-- profiles carry secret_value_stored=false and external_call_allowed=false; the readiness view
-- keeps ready_for_api_call_test hard-false and active_key_profiles / external_call_allowed /
-- publish-permission / send-permission counts at 0.

CREATE TABLE IF NOT EXISTS wix_api_permission_catalog (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  permission_key text,
  permission_display_name text,
  permission_category text,
  recommended_status text DEFAULT 'research',
  risk_level text DEFAULT 'medium',
  useful_for jsonb DEFAULT '[]'::jsonb,
  blocked_reason text,
  safe_summary text,
  official_doc_url text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wapc_permission_key ON wix_api_permission_catalog(permission_key);
CREATE INDEX IF NOT EXISTS idx_wapc_permission_category ON wix_api_permission_catalog(permission_category);
CREATE INDEX IF NOT EXISTS idx_wapc_recommended_status ON wix_api_permission_catalog(recommended_status);
CREATE INDEX IF NOT EXISTS idx_wapc_risk_level ON wix_api_permission_catalog(risk_level);
CREATE INDEX IF NOT EXISTS idx_wapc_created_at ON wix_api_permission_catalog(created_at);

CREATE TABLE IF NOT EXISTS wix_api_integration_use_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  permission_catalog_id uuid REFERENCES wix_api_permission_catalog(id),
  use_case_key text,
  use_case_area text,
  use_case_status text DEFAULT 'planned',
  requires_api_key boolean DEFAULT true,
  requires_site_id boolean DEFAULT true,
  requires_account_id boolean DEFAULT false,
  can_run_read_only boolean DEFAULT true,
  can_write boolean DEFAULT false,
  can_publish boolean DEFAULT false,
  can_send_messages boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waiuc_permission_catalog_id ON wix_api_integration_use_cases(permission_catalog_id);
CREATE INDEX IF NOT EXISTS idx_waiuc_use_case_key ON wix_api_integration_use_cases(use_case_key);
CREATE INDEX IF NOT EXISTS idx_waiuc_use_case_area ON wix_api_integration_use_cases(use_case_area);
CREATE INDEX IF NOT EXISTS idx_waiuc_use_case_status ON wix_api_integration_use_cases(use_case_status);
CREATE INDEX IF NOT EXISTS idx_waiuc_created_at ON wix_api_integration_use_cases(created_at);

CREATE TABLE IF NOT EXISTS wix_api_key_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_key text,
  profile_status text DEFAULT 'planned',
  environment text,
  purpose text,
  allowed_permission_keys jsonb DEFAULT '[]'::jsonb,
  forbidden_permission_keys jsonb DEFAULT '[]'::jsonb,
  secret_value_stored boolean DEFAULT false,
  secret_location text,
  external_call_allowed boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wakp_profile_key ON wix_api_key_profiles(profile_key);
CREATE INDEX IF NOT EXISTS idx_wakp_profile_status ON wix_api_key_profiles(profile_status);
CREATE INDEX IF NOT EXISTS idx_wakp_environment ON wix_api_key_profiles(environment);
CREATE INDEX IF NOT EXISTS idx_wakp_created_at ON wix_api_key_profiles(created_at);

CREATE TABLE IF NOT EXISTS wix_api_permission_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  permission_catalog_id uuid REFERENCES wix_api_permission_catalog(id),
  key_profile_id uuid REFERENCES wix_api_key_profiles(id),
  use_case_id uuid REFERENCES wix_api_integration_use_cases(id),
  review_type text,
  status text DEFAULT 'pending',
  priority text DEFAULT 'normal',
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wapri_permission_catalog_id ON wix_api_permission_review_items(permission_catalog_id);
CREATE INDEX IF NOT EXISTS idx_wapri_key_profile_id ON wix_api_permission_review_items(key_profile_id);
CREATE INDEX IF NOT EXISTS idx_wapri_use_case_id ON wix_api_permission_review_items(use_case_id);
CREATE INDEX IF NOT EXISTS idx_wapri_review_type ON wix_api_permission_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_wapri_status ON wix_api_permission_review_items(status);
CREATE INDEX IF NOT EXISTS idx_wapri_created_at ON wix_api_permission_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_api_permission_catalog_updated_at ON wix_api_permission_catalog;
CREATE TRIGGER trg_wix_api_permission_catalog_updated_at
BEFORE UPDATE ON wix_api_permission_catalog FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_api_integration_use_cases_updated_at ON wix_api_integration_use_cases;
CREATE TRIGGER trg_wix_api_integration_use_cases_updated_at
BEFORE UPDATE ON wix_api_integration_use_cases FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_api_key_profiles_updated_at ON wix_api_key_profiles;
CREATE TRIGGER trg_wix_api_key_profiles_updated_at
BEFORE UPDATE ON wix_api_key_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_api_permission_review_items_updated_at ON wix_api_permission_review_items;
CREATE TRIGGER trg_wix_api_permission_review_items_updated_at
BEFORE UPDATE ON wix_api_permission_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_api_permission_catalog_dashboard AS
SELECT
  c.permission_key,
  c.permission_display_name,
  c.permission_category,
  c.recommended_status,
  c.risk_level,
  c.useful_for,
  c.blocked_reason,
  c.safe_summary,
  c.created_at
FROM wix_api_permission_catalog c;

CREATE OR REPLACE VIEW vw_wix_api_integration_use_case_dashboard AS
SELECT
  u.use_case_key,
  u.use_case_area,
  u.use_case_status,
  c.permission_key,
  c.permission_category,
  u.requires_api_key,
  u.requires_site_id,
  u.requires_account_id,
  u.can_run_read_only,
  u.can_write,
  u.can_publish,
  u.can_send_messages,
  u.safe_summary
FROM wix_api_integration_use_cases u
LEFT JOIN wix_api_permission_catalog c ON c.id = u.permission_catalog_id;

CREATE OR REPLACE VIEW vw_wix_api_key_profile_dashboard AS
SELECT
  k.profile_key,
  k.profile_status,
  k.environment,
  k.purpose,
  k.allowed_permission_keys,
  k.forbidden_permission_keys,
  k.secret_value_stored,
  k.secret_location,
  k.external_call_allowed,
  k.safe_summary,
  k.created_at
FROM wix_api_key_profiles k;

CREATE OR REPLACE VIEW vw_wix_api_permission_review_queue AS
SELECT
  ri.id AS review_item_id,
  ri.review_type,
  ri.status,
  ri.priority,
  c.permission_key,
  k.profile_key,
  u.use_case_key,
  ri.created_at
FROM wix_api_permission_review_items ri
LEFT JOIN wix_api_permission_catalog c ON c.id = ri.permission_catalog_id
LEFT JOIN wix_api_key_profiles k ON k.id = ri.key_profile_id
LEFT JOIN wix_api_integration_use_cases u ON u.id = ri.use_case_id;

CREATE OR REPLACE VIEW vw_dlf_wix_api_readiness AS
WITH agg AS (
  SELECT
    (SELECT count(*) FROM wix_api_permission_catalog) AS permission_catalog_rows,
    (SELECT count(*) FROM wix_api_permission_catalog WHERE recommended_status = 'allow_now') AS allowed_now_count,
    (SELECT count(*) FROM wix_api_permission_catalog WHERE recommended_status = 'allow_staging_only') AS allow_staging_only_count,
    (SELECT count(*) FROM wix_api_permission_catalog WHERE recommended_status IN ('defer', 'allow_later')) AS deferred_count,
    (SELECT count(*) FROM wix_api_permission_catalog WHERE recommended_status = 'avoid') AS avoid_count,
    (SELECT count(*) FROM wix_api_key_profiles) AS key_profiles,
    (SELECT count(*) FROM wix_api_key_profiles WHERE profile_status = 'active') AS active_key_profiles,
    (SELECT count(*) FROM wix_api_key_profiles WHERE external_call_allowed IS TRUE) AS external_call_allowed_count,
    (SELECT count(*) FROM wix_api_key_profiles WHERE secret_value_stored IS TRUE) AS secret_value_stored_count,
    (SELECT count(*) FROM wix_api_integration_use_cases WHERE can_publish IS TRUE AND use_case_status = 'approved_for_staging') AS publish_permission_allowed_count,
    (SELECT count(*) FROM wix_api_integration_use_cases WHERE can_send_messages IS TRUE AND use_case_status = 'approved_for_staging') AS send_permission_allowed_count,
    (SELECT count(*) FROM wix_api_permission_review_items WHERE status = 'pending') AS pending_reviews,
    (SELECT count(*) FROM wix_api_permission_review_items WHERE status = 'approved') AS approved_reviews
)
SELECT
  permission_catalog_rows,
  allowed_now_count,
  allow_staging_only_count,
  deferred_count,
  avoid_count,
  key_profiles,
  active_key_profiles,
  external_call_allowed_count,
  publish_permission_allowed_count,
  send_permission_allowed_count,
  (
    permission_catalog_rows > 0
    AND key_profiles > 0
    AND external_call_allowed_count = 0
    AND secret_value_stored_count = 0
    AND active_key_profiles = 0
    AND approved_reviews > 0
    AND pending_reviews = 0
  ) AS ready_for_api_key_creation,
  false AS ready_for_api_call_test,
  CASE
    WHEN external_call_allowed_count > 0 THEN 'blocked: a key profile has external_call_allowed'
    WHEN secret_value_stored_count > 0 THEN 'blocked: a key profile reports secret_value_stored'
    WHEN active_key_profiles > 0 THEN 'blocked: a key profile is active'
    WHEN permission_catalog_rows = 0 THEN 'blocked: no permission catalog mapped'
    WHEN key_profiles = 0 THEN 'blocked: no key profile planned'
    WHEN pending_reviews > 0 THEN 'capability map under human review; no API key creation yet'
    WHEN approved_reviews = 0 THEN 'capability map seeded; awaiting human approval before any API key creation'
    ELSE 'permission map approved; operator may create a staging API key EXTERNALLY (key never enters repo/prompt); API call test stays a separate gated phase'
  END AS blocked_reason
FROM agg;
