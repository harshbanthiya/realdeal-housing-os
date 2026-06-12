-- Phase 7.17: Fable / Gemini design output capture and refinement review for DLF Westpark.
--
-- Captures the manually-generated Fable "Gallery White" website design direction and
-- the Gemini second-opinion critique into review-gated tracking tables, and records the
-- concrete design refinement actions extracted from that critique. This schema only
-- creates tracking/review tables and count-safe dashboards. It performs NO Fable call,
-- NO Gemini call, NO Wix API call, NO external API call, NO publishing, NO live
-- form/webhook, NO sends, and NO inbound-lead/contact writes. Raw Fable/Gemini artifacts
-- are NEVER stored in the database (only filesystem paths under the git-ignored exports/
-- tree). external_call_made stays false and the readiness view keeps
-- ready_for_wix_design_build gated on human review.

CREATE TABLE IF NOT EXISTS fable_design_outputs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  handoff_package_id uuid REFERENCES fable_uiux_handoff_packages(id),
  output_key text,
  output_status text DEFAULT 'captured',
  design_direction_name text,
  source_tool text DEFAULT 'fable',
  raw_artifact_path text,
  preview_artifact_path text,
  safe_summary text,
  contains_private_contact_data boolean DEFAULT false,
  contains_secrets boolean DEFAULT false,
  contains_unverified_claims boolean DEFAULT true,
  external_call_made boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fdo_launch_project_id ON fable_design_outputs(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_fdo_output_key ON fable_design_outputs(output_key);
CREATE INDEX IF NOT EXISTS idx_fdo_output_status ON fable_design_outputs(output_status);
CREATE INDEX IF NOT EXISTS idx_fdo_created_at ON fable_design_outputs(created_at);

CREATE TABLE IF NOT EXISTS design_second_opinion_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  fable_design_output_id uuid REFERENCES fable_design_outputs(id),
  review_key text,
  review_source text,
  review_status text DEFAULT 'captured',
  raw_artifact_path text,
  safe_summary text,
  contains_private_contact_data boolean DEFAULT false,
  contains_secrets boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsor_launch_project_id ON design_second_opinion_reviews(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_dsor_fable_design_output_id ON design_second_opinion_reviews(fable_design_output_id);
CREATE INDEX IF NOT EXISTS idx_dsor_review_key ON design_second_opinion_reviews(review_key);
CREATE INDEX IF NOT EXISTS idx_dsor_review_status ON design_second_opinion_reviews(review_status);
CREATE INDEX IF NOT EXISTS idx_dsor_created_at ON design_second_opinion_reviews(created_at);

CREATE TABLE IF NOT EXISTS design_refinement_actions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  fable_design_output_id uuid REFERENCES fable_design_outputs(id),
  second_opinion_review_id uuid REFERENCES design_second_opinion_reviews(id),
  action_key text,
  action_category text,
  action_status text DEFAULT 'proposed',
  priority text DEFAULT 'normal',
  safe_summary text,
  wix_implementation_note text,
  fable_followup_note text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dra_launch_project_id ON design_refinement_actions(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_dra_fable_design_output_id ON design_refinement_actions(fable_design_output_id);
CREATE INDEX IF NOT EXISTS idx_dra_second_opinion_review_id ON design_refinement_actions(second_opinion_review_id);
CREATE INDEX IF NOT EXISTS idx_dra_action_key ON design_refinement_actions(action_key);
CREATE INDEX IF NOT EXISTS idx_dra_action_category ON design_refinement_actions(action_category);
CREATE INDEX IF NOT EXISTS idx_dra_action_status ON design_refinement_actions(action_status);
CREATE INDEX IF NOT EXISTS idx_dra_priority ON design_refinement_actions(priority);
CREATE INDEX IF NOT EXISTS idx_dra_created_at ON design_refinement_actions(created_at);

CREATE TABLE IF NOT EXISTS fable_design_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  fable_design_output_id uuid REFERENCES fable_design_outputs(id),
  second_opinion_review_id uuid REFERENCES design_second_opinion_reviews(id),
  refinement_action_id uuid REFERENCES design_refinement_actions(id),
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

CREATE INDEX IF NOT EXISTS idx_fdri_launch_project_id ON fable_design_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_fdri_fable_design_output_id ON fable_design_review_items(fable_design_output_id);
CREATE INDEX IF NOT EXISTS idx_fdri_second_opinion_review_id ON fable_design_review_items(second_opinion_review_id);
CREATE INDEX IF NOT EXISTS idx_fdri_refinement_action_id ON fable_design_review_items(refinement_action_id);
CREATE INDEX IF NOT EXISTS idx_fdri_review_type ON fable_design_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_fdri_status ON fable_design_review_items(status);
CREATE INDEX IF NOT EXISTS idx_fdri_priority ON fable_design_review_items(priority);
CREATE INDEX IF NOT EXISTS idx_fdri_created_at ON fable_design_review_items(created_at);

DROP TRIGGER IF EXISTS trg_fable_design_outputs_updated_at ON fable_design_outputs;
CREATE TRIGGER trg_fable_design_outputs_updated_at
BEFORE UPDATE ON fable_design_outputs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_design_second_opinion_reviews_updated_at ON design_second_opinion_reviews;
CREATE TRIGGER trg_design_second_opinion_reviews_updated_at
BEFORE UPDATE ON design_second_opinion_reviews FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_design_refinement_actions_updated_at ON design_refinement_actions;
CREATE TRIGGER trg_design_refinement_actions_updated_at
BEFORE UPDATE ON design_refinement_actions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fable_design_review_items_updated_at ON fable_design_review_items;
CREATE TRIGGER trg_fable_design_review_items_updated_at
BEFORE UPDATE ON fable_design_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_fable_design_output_dashboard AS
SELECT
  p.launch_key,
  o.output_key,
  o.output_status,
  o.design_direction_name,
  o.source_tool,
  o.contains_private_contact_data,
  o.contains_secrets,
  o.contains_unverified_claims,
  o.external_call_made,
  o.human_review_required,
  o.created_at
FROM fable_design_outputs o
JOIN launch_projects p ON p.id = o.launch_project_id;

CREATE OR REPLACE VIEW vw_design_second_opinion_dashboard AS
SELECT
  p.launch_key,
  r.review_key,
  r.review_source,
  r.review_status,
  r.contains_private_contact_data,
  r.contains_secrets,
  r.external_call_made,
  r.safe_summary,
  r.created_at
FROM design_second_opinion_reviews r
JOIN launch_projects p ON p.id = r.launch_project_id;

CREATE OR REPLACE VIEW vw_design_refinement_action_dashboard AS
SELECT
  p.launch_key,
  a.action_key,
  a.action_category,
  a.action_status,
  a.priority,
  a.safe_summary,
  a.wix_implementation_note
FROM design_refinement_actions a
JOIN launch_projects p ON p.id = a.launch_project_id;

CREATE OR REPLACE VIEW vw_fable_design_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  ri.review_type,
  ri.status,
  ri.priority,
  COALESCE(
    'action:' || a.action_key,
    'second_opinion:' || r.review_key,
    'output:' || o.output_key
  ) AS linked_area,
  ri.created_at
FROM fable_design_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN fable_design_outputs o ON o.id = ri.fable_design_output_id
LEFT JOIN design_second_opinion_reviews r ON r.id = ri.second_opinion_review_id
LEFT JOIN design_refinement_actions a ON a.id = ri.refinement_action_id;

CREATE OR REPLACE VIEW vw_dlf_design_output_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    count(DISTINCT o.id) AS design_outputs,
    count(DISTINCT r.id) AS second_opinion_reviews,
    count(DISTINCT a.id) AS refinement_actions,
    count(DISTINCT a.id) FILTER (WHERE a.action_status = 'accepted') AS accepted_actions,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    count(DISTINCT o.id) FILTER (WHERE o.output_status = 'accepted_direction') AS output_accepted_count,
    count(DISTINCT o.id) FILTER (WHERE o.external_call_made IS TRUE) AS output_external_call_made_count,
    count(DISTINCT r.id) FILTER (WHERE r.external_call_made IS TRUE) AS review_external_call_made_count,
    count(DISTINCT o.id) FILTER (
      WHERE o.contains_private_contact_data IS TRUE
         OR o.contains_secrets IS TRUE
    ) AS unsafe_output_flags,
    count(DISTINCT r.id) FILTER (
      WHERE r.contains_private_contact_data IS TRUE
         OR r.contains_secrets IS TRUE
    ) AS unsafe_review_flags
  FROM launch_scope p
  LEFT JOIN fable_design_outputs o ON o.launch_project_id = p.id
  LEFT JOIN design_second_opinion_reviews r ON r.launch_project_id = p.id
  LEFT JOIN design_refinement_actions a ON a.launch_project_id = p.id
  LEFT JOIN fable_design_review_items ri ON ri.launch_project_id = p.id
  GROUP BY p.id, p.launch_key
)
SELECT
  launch_key,
  design_outputs,
  second_opinion_reviews,
  refinement_actions,
  accepted_actions,
  pending_reviews,
  output_accepted_count,
  (output_external_call_made_count + review_external_call_made_count) AS external_call_made_count,
  (
    design_outputs > 0
    AND output_accepted_count > 0
    AND (output_external_call_made_count + review_external_call_made_count) = 0
    AND unsafe_output_flags = 0
    AND unsafe_review_flags = 0
  ) AS ready_for_fable_followup,
  (
    design_outputs > 0
    AND output_accepted_count > 0
    AND accepted_actions > 0
    AND pending_reviews = 0
    AND (output_external_call_made_count + review_external_call_made_count) = 0
    AND unsafe_output_flags = 0
    AND unsafe_review_flags = 0
  ) AS ready_for_wix_design_build,
  CASE
    WHEN (output_external_call_made_count + review_external_call_made_count) > 0 THEN 'blocked: row marked external_call_made'
    WHEN (unsafe_output_flags + unsafe_review_flags) > 0 THEN 'blocked: row flagged with contact data or secrets'
    WHEN design_outputs = 0 THEN 'blocked: no Fable design output captured'
    WHEN output_accepted_count = 0 THEN 'blocked: design output not yet accepted as direction'
    WHEN accepted_actions = 0 THEN 'blocked: no refinement action accepted'
    WHEN pending_reviews > 0 THEN 'blocked: pending human design reviews'
    ELSE 'approved: refined design direction accepted; operator may build the Wix design or craft a Fable follow-up prompt manually'
  END AS blocked_reason
FROM agg;
