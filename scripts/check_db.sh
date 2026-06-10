#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  echo "Create it from docker/.env.example before checking the database."
  exit 1
fi

DOCKER_BIN="${DOCKER_BIN:-docker}"
if ! command -v "$DOCKER_BIN" >/dev/null 2>&1; then
  if [ -x /usr/local/bin/docker ]; then
    DOCKER_BIN=/usr/local/bin/docker
  elif [ -x /Applications/Docker.app/Contents/Resources/bin/docker ]; then
    DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
  else
    echo "Docker CLI was not found. Start Docker Desktop and try again."
    exit 1
  fi
fi

read_env_value() {
  local key="$1"
  grep "^${key}=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2-
}

POSTGRES_USER="$(read_env_value POSTGRES_USER)"
POSTGRES_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
POSTGRES_DB="$(read_env_value POSTGRES_DB)"

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
  echo "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in $ENV_FILE"
  exit 1
fi

DB_NAME="${POSTGRES_DB:-realdeal_os}"
EXPECTED_TABLES="'contacts','buildings','inventory','media_assets','content_items','interactions','tasks','import_batches','contact_import_rows','contact_aliases','contact_property_hints','contact_duplicate_candidates','source_files','contact_methods','lead_requirements','inventory_import_rows','import_review_items','review_action_log','canonical_merge_batches','canonical_merge_links','building_aliases','building_units','contact_property_relationships','property_relationship_review_items','property_relationship_action_log','building_web_profiles','seo_keywords','content_briefs','content_publishing_queue','inbound_lead_sources','inbound_leads','lead_attribution_events','channel_permissions','outreach_suppression_list','campaign_drafts','ai_agent_tasks','wix_cms_collections','wix_cms_field_mappings','content_review_items','publishing_readiness_checks','content_quality_checks','content_source_requirements','ai_prompt_templates','ai_task_execution_plans','content_draft_artifacts','content_draft_reviews','content_source_gap_items','source_gap_resolution_tasks','internal_source_evidence','source_gap_review_items','building_duplicate_candidates','building_dedupe_review_items','building_dedupe_action_log','rera_project_profiles','rera_building_match_candidates','rera_carpet_area_records','rera_project_status_checks','rera_area_mismatch_candidates','rera_verification_review_items','rera_snapshot_captures','rera_parsed_fact_candidates','rera_snapshot_compare_results','rera_snapshot_review_items','launch_projects','launch_channels','launch_campaign_calendar','launch_lead_segments','launch_operator_tasks','launch_readiness_checks','launch_landing_page_specs','launch_lead_capture_forms','launch_utm_campaign_specs','launch_content_pillars','launch_message_templates','launch_social_content_drafts','launch_lead_scoring_rules','launch_draft_review_items','launch_contact_segment_candidates','launch_contact_permission_review_items','launch_contact_segment_audit_log','launch_lead_intake_endpoints','launch_lead_field_mappings','launch_lead_attribution_rules','launch_inbound_lead_review_items','launch_operator_daily_metrics'"
EXPECTED_VIEWS="'vw_import_contact_review','vw_duplicate_review','vw_inventory_import_review','vw_lead_requirements_review','vw_review_dashboard_summary','vw_review_contact_methods','vw_review_business_leads','vw_review_duplicate_candidates','vw_review_queue','vw_review_batch_sources','vw_canonical_merge_batches','vw_canonical_merge_links','vw_canonical_contacts_review','vw_canonical_contact_methods_review','vw_canonical_source_trace','vw_canonical_lead_requirements_review','vw_canonical_merge_audit','vw_building_alias_review','vw_building_units_review','vw_contact_property_relationship_review','vw_property_relationship_review_queue','vw_contact_building_unit_trace','vw_owner_relationship_dashboard','vw_building_unit_owner_summary','vw_contact_property_trace_full','vw_property_relationship_revert_readiness','vw_milestone_2b_summary','vw_owner_unit_batch_quality','vw_owner_unit_candidate_queue','vw_owner_relationship_revert_dashboard','vw_duplicate_risk_dashboard','vw_human_dashboard_home','vw_human_next_actions','vw_human_owner_relationships','vw_human_candidate_review_queue','vw_growth_pipeline_home','vw_seo_keyword_dashboard','vw_content_pipeline_dashboard','vw_inbound_lead_review_queue','vw_channel_permission_dashboard','vw_campaign_readiness_dashboard','vw_ai_agent_task_dashboard','vw_wix_cms_mapping_dashboard','vw_content_review_dashboard','vw_publishing_readiness_dashboard','vw_imperial_heights_content_plan','vw_content_quality_dashboard','vw_content_source_requirements_dashboard','vw_ai_prompt_template_dashboard','vw_ai_task_execution_plan_dashboard','vw_imperial_heights_content_readiness','vw_content_draft_artifact_dashboard','vw_content_draft_review_queue','vw_content_source_gap_dashboard','vw_imperial_heights_draft_workspace','vw_source_gap_resolution_dashboard','vw_internal_source_evidence_dashboard','vw_source_gap_review_queue','vw_imperial_heights_source_gap_status','vw_internal_evidence_acceptance_dashboard','vw_imperial_heights_evidence_readiness','vw_building_dedupe_dashboard','vw_imperial_heights_building_anchor_summary','vw_building_dedupe_review_queue','vw_rera_project_verification_dashboard','vw_rera_building_match_dashboard','vw_rera_area_mismatch_dashboard','vw_rera_status_risk_dashboard','vw_rera_verification_review_queue','vw_imperial_heights_rera_readiness','vw_rera_snapshot_capture_dashboard','vw_rera_parsed_fact_candidate_dashboard','vw_rera_snapshot_compare_dashboard','vw_rera_snapshot_review_queue','vw_imperial_heights_rera_parser_readiness','vw_launch_command_center_home','vw_launch_channel_dashboard','vw_launch_calendar_dashboard','vw_launch_lead_segment_dashboard','vw_launch_operator_task_dashboard','vw_launch_readiness_dashboard','vw_dlf_launch_priority_dashboard','vw_launch_landing_page_dashboard','vw_launch_lead_capture_form_dashboard','vw_launch_utm_campaign_dashboard','vw_launch_content_pillar_dashboard','vw_launch_message_template_dashboard','vw_launch_social_content_dashboard','vw_launch_lead_scoring_dashboard','vw_launch_draft_review_queue','vw_dlf_launch_funnel_readiness','vw_launch_contact_segment_candidate_dashboard','vw_launch_contact_permission_review_queue','vw_dlf_contact_segment_readiness','vw_dlf_owner_audience_summary','vw_launch_lead_intake_endpoint_dashboard','vw_launch_lead_field_mapping_dashboard','vw_launch_lead_attribution_rule_dashboard','vw_launch_inbound_lead_review_dashboard','vw_launch_operator_daily_metrics_dashboard','vw_dlf_lead_intake_readiness'"

echo "Checking Real Deal OS tables in database: $DB_NAME"

"$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
WITH expected(table_name) AS (
  VALUES
    ('contacts'),
    ('buildings'),
    ('inventory'),
    ('media_assets'),
    ('content_items'),
    ('interactions'),
    ('tasks'),
    ('import_batches'),
    ('contact_import_rows'),
    ('contact_aliases'),
    ('contact_property_hints'),
    ('contact_duplicate_candidates'),
    ('source_files'),
    ('contact_methods'),
    ('lead_requirements'),
    ('inventory_import_rows'),
    ('import_review_items'),
    ('review_action_log'),
    ('canonical_merge_batches'),
    ('canonical_merge_links'),
    ('building_aliases'),
    ('building_units'),
    ('contact_property_relationships'),
    ('property_relationship_review_items'),
    ('property_relationship_action_log'),
    ('building_web_profiles'),
    ('seo_keywords'),
    ('content_briefs'),
    ('content_publishing_queue'),
    ('inbound_lead_sources'),
    ('inbound_leads'),
    ('lead_attribution_events'),
    ('channel_permissions'),
    ('outreach_suppression_list'),
    ('campaign_drafts'),
    ('ai_agent_tasks'),
    ('wix_cms_collections'),
    ('wix_cms_field_mappings'),
    ('content_review_items'),
    ('publishing_readiness_checks'),
    ('content_quality_checks'),
    ('content_source_requirements'),
    ('ai_prompt_templates'),
    ('ai_task_execution_plans'),
    ('content_draft_artifacts'),
    ('content_draft_reviews'),
    ('content_source_gap_items'),
    ('source_gap_resolution_tasks'),
    ('internal_source_evidence'),
    ('source_gap_review_items'),
    ('building_duplicate_candidates'),
    ('building_dedupe_review_items'),
    ('building_dedupe_action_log'),
    ('rera_project_profiles'),
    ('rera_building_match_candidates'),
    ('rera_carpet_area_records'),
    ('rera_project_status_checks'),
    ('rera_area_mismatch_candidates'),
    ('rera_verification_review_items'),
    ('rera_snapshot_captures'),
    ('rera_parsed_fact_candidates'),
    ('rera_snapshot_compare_results'),
    ('rera_snapshot_review_items'),
    ('launch_projects'),
    ('launch_channels'),
    ('launch_campaign_calendar'),
    ('launch_lead_segments'),
    ('launch_operator_tasks'),
    ('launch_readiness_checks'),
    ('launch_landing_page_specs'),
    ('launch_lead_capture_forms'),
    ('launch_utm_campaign_specs'),
    ('launch_content_pillars'),
    ('launch_message_templates'),
    ('launch_social_content_drafts'),
    ('launch_lead_scoring_rules'),
    ('launch_draft_review_items'),
    ('launch_contact_segment_candidates'),
    ('launch_contact_permission_review_items'),
    ('launch_contact_segment_audit_log'),
    ('launch_lead_intake_endpoints'),
    ('launch_lead_field_mappings'),
    ('launch_lead_attribution_rules'),
    ('launch_inbound_lead_review_items'),
    ('launch_operator_daily_metrics')
)
SELECT
  expected.table_name,
  CASE WHEN tables.table_name IS NULL THEN 'missing' ELSE 'ok' END AS status
FROM expected
LEFT JOIN information_schema.tables tables
  ON tables.table_schema = 'public'
 AND tables.table_name = expected.table_name
ORDER BY expected.table_name;
"

MISSING_COUNT="$("$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -At -v ON_ERROR_STOP=1 -c "
WITH expected(table_name) AS (
  SELECT unnest(ARRAY[$EXPECTED_TABLES])
)
SELECT count(*)
FROM expected
LEFT JOIN information_schema.tables tables
  ON tables.table_schema = 'public'
 AND tables.table_name = expected.table_name
WHERE tables.table_name IS NULL;
")"

if [ "$MISSING_COUNT" != "0" ]; then
  echo "Database check failed: $MISSING_COUNT expected table(s) are missing."
  exit 1
fi

echo "Checking Real Deal OS review views in database: $DB_NAME"

"$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
WITH expected(view_name) AS (
  VALUES
    ('vw_import_contact_review'),
    ('vw_duplicate_review'),
    ('vw_inventory_import_review'),
    ('vw_lead_requirements_review'),
    ('vw_review_dashboard_summary'),
    ('vw_review_contact_methods'),
    ('vw_review_business_leads'),
    ('vw_review_duplicate_candidates'),
    ('vw_review_queue'),
    ('vw_review_batch_sources'),
    ('vw_canonical_merge_batches'),
    ('vw_canonical_merge_links'),
    ('vw_canonical_contacts_review'),
    ('vw_canonical_contact_methods_review'),
    ('vw_canonical_source_trace'),
    ('vw_canonical_lead_requirements_review'),
    ('vw_canonical_merge_audit'),
    ('vw_building_alias_review'),
    ('vw_building_units_review'),
    ('vw_contact_property_relationship_review'),
    ('vw_property_relationship_review_queue'),
    ('vw_contact_building_unit_trace'),
    ('vw_owner_relationship_dashboard'),
    ('vw_building_unit_owner_summary'),
    ('vw_contact_property_trace_full'),
    ('vw_property_relationship_revert_readiness'),
    ('vw_milestone_2b_summary'),
    ('vw_owner_unit_batch_quality'),
    ('vw_owner_unit_candidate_queue'),
    ('vw_owner_relationship_revert_dashboard'),
    ('vw_duplicate_risk_dashboard'),
    ('vw_human_dashboard_home'),
    ('vw_human_next_actions'),
    ('vw_human_owner_relationships'),
    ('vw_human_candidate_review_queue'),
    ('vw_growth_pipeline_home'),
    ('vw_seo_keyword_dashboard'),
    ('vw_content_pipeline_dashboard'),
    ('vw_inbound_lead_review_queue'),
    ('vw_channel_permission_dashboard'),
    ('vw_campaign_readiness_dashboard'),
    ('vw_ai_agent_task_dashboard'),
    ('vw_wix_cms_mapping_dashboard'),
    ('vw_content_review_dashboard'),
    ('vw_publishing_readiness_dashboard'),
    ('vw_imperial_heights_content_plan'),
    ('vw_content_quality_dashboard'),
    ('vw_content_source_requirements_dashboard'),
    ('vw_ai_prompt_template_dashboard'),
    ('vw_ai_task_execution_plan_dashboard'),
    ('vw_imperial_heights_content_readiness'),
    ('vw_content_draft_artifact_dashboard'),
    ('vw_content_draft_review_queue'),
    ('vw_content_source_gap_dashboard'),
    ('vw_imperial_heights_draft_workspace'),
    ('vw_source_gap_resolution_dashboard'),
    ('vw_internal_source_evidence_dashboard'),
    ('vw_source_gap_review_queue'),
    ('vw_imperial_heights_source_gap_status'),
    ('vw_internal_evidence_acceptance_dashboard'),
    ('vw_imperial_heights_evidence_readiness'),
    ('vw_building_dedupe_dashboard'),
    ('vw_imperial_heights_building_anchor_summary'),
    ('vw_building_dedupe_review_queue'),
    ('vw_rera_project_verification_dashboard'),
    ('vw_rera_building_match_dashboard'),
    ('vw_rera_area_mismatch_dashboard'),
    ('vw_rera_status_risk_dashboard'),
    ('vw_rera_verification_review_queue'),
    ('vw_imperial_heights_rera_readiness'),
    ('vw_rera_snapshot_capture_dashboard'),
    ('vw_rera_parsed_fact_candidate_dashboard'),
    ('vw_rera_snapshot_compare_dashboard'),
    ('vw_rera_snapshot_review_queue'),
    ('vw_imperial_heights_rera_parser_readiness'),
    ('vw_launch_command_center_home'),
    ('vw_launch_channel_dashboard'),
    ('vw_launch_calendar_dashboard'),
    ('vw_launch_lead_segment_dashboard'),
    ('vw_launch_operator_task_dashboard'),
    ('vw_launch_readiness_dashboard'),
    ('vw_dlf_launch_priority_dashboard'),
    ('vw_launch_landing_page_dashboard'),
    ('vw_launch_lead_capture_form_dashboard'),
    ('vw_launch_utm_campaign_dashboard'),
    ('vw_launch_content_pillar_dashboard'),
    ('vw_launch_message_template_dashboard'),
    ('vw_launch_social_content_dashboard'),
    ('vw_launch_lead_scoring_dashboard'),
    ('vw_launch_draft_review_queue'),
    ('vw_dlf_launch_funnel_readiness'),
    ('vw_launch_contact_segment_candidate_dashboard'),
    ('vw_launch_contact_permission_review_queue'),
    ('vw_dlf_contact_segment_readiness'),
    ('vw_dlf_owner_audience_summary'),
    ('vw_launch_lead_intake_endpoint_dashboard'),
    ('vw_launch_lead_field_mapping_dashboard'),
    ('vw_launch_lead_attribution_rule_dashboard'),
    ('vw_launch_inbound_lead_review_dashboard'),
    ('vw_launch_operator_daily_metrics_dashboard'),
    ('vw_dlf_lead_intake_readiness')
)
SELECT
  expected.view_name,
  CASE WHEN views.table_name IS NULL THEN 'missing' ELSE 'ok' END AS status
FROM expected
LEFT JOIN information_schema.views views
  ON views.table_schema = 'public'
 AND views.table_name = expected.view_name
ORDER BY expected.view_name;
"

MISSING_VIEW_COUNT="$("$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -At -v ON_ERROR_STOP=1 -c "
WITH expected(view_name) AS (
  SELECT unnest(ARRAY[$EXPECTED_VIEWS])
)
SELECT count(*)
FROM expected
LEFT JOIN information_schema.views views
  ON views.table_schema = 'public'
 AND views.table_name = expected.view_name
WHERE views.table_name IS NULL;
")"

if [ "$MISSING_VIEW_COUNT" != "0" ]; then
  echo "Database check failed: $MISSING_VIEW_COUNT expected view(s) are missing."
  exit 1
fi

echo "Database check passed: all expected Real Deal OS tables and views exist."
