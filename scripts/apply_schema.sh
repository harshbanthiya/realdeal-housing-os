#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
SCHEMA_FILES=(
  "$PROJECT_ROOT/schemas/001_initial_schema.sql"
  "$PROJECT_ROOT/schemas/002_contact_import_extensions.sql"
  "$PROJECT_ROOT/schemas/003_source_aware_import_schema.sql"
  "$PROJECT_ROOT/schemas/004_nocodb_review_workflow.sql"
  "$PROJECT_ROOT/schemas/005_review_action_statuses.sql"
  "$PROJECT_ROOT/schemas/006_canonical_merge_workflow.sql"
  "$PROJECT_ROOT/schemas/007_canonical_review_dashboard.sql"
  "$PROJECT_ROOT/schemas/008_property_relationship_pipeline.sql"
  "$PROJECT_ROOT/schemas/009_owner_building_unit_dashboard.sql"
  "$PROJECT_ROOT/schemas/010_milestone_2b_data_quality_dashboard.sql"
  "$PROJECT_ROOT/schemas/011_human_dashboard_ops_views.sql"
  "$PROJECT_ROOT/schemas/012_growth_seo_lead_pipeline.sql"
  "$PROJECT_ROOT/schemas/013_wix_cms_content_readiness.sql"
  "$PROJECT_ROOT/schemas/014_content_quality_and_ai_planning.sql"
  "$PROJECT_ROOT/schemas/015_content_draft_workspace.sql"
  "$PROJECT_ROOT/schemas/016_source_gap_resolution_workflow.sql"
  "$PROJECT_ROOT/schemas/017_internal_evidence_acceptance_dashboard.sql"
  "$PROJECT_ROOT/schemas/018_building_dedupe_review_workflow.sql"
  "$PROJECT_ROOT/schemas/019_rera_verification_foundation.sql"
  "$PROJECT_ROOT/schemas/020_rera_snapshot_parser_staging.sql"
  "$PROJECT_ROOT/schemas/021_launch_command_center.sql"
  "$PROJECT_ROOT/schemas/022_launch_funnel_workspace.sql"
  "$PROJECT_ROOT/schemas/023_launch_contact_segmentation.sql"
  "$PROJECT_ROOT/schemas/024_dlf_lead_intake_attribution.sql"
  "$PROJECT_ROOT/schemas/025_n8n_launch_workflow_blueprint.sql"
  "$PROJECT_ROOT/schemas/026_dlf_operator_cockpit.sql"
  "$PROJECT_ROOT/schemas/027_dlf_launch_blocker_triage.sql"
  "$PROJECT_ROOT/schemas/029_dlf_consent_privacy_readiness.sql"
  "$PROJECT_ROOT/schemas/030_dlf_contact_permission_evidence.sql"
  "$PROJECT_ROOT/schemas/031_dlf_test_lead_intake_harness.sql"
  "$PROJECT_ROOT/schemas/032_dlf_n8n_build_package.sql"
  "$PROJECT_ROOT/schemas/033_dlf_n8n_manual_import_verification.sql"
  "$PROJECT_ROOT/schemas/034_dlf_wix_landing_build_package.sql"
  "$PROJECT_ROOT/schemas/035_wix_ux_integration_masterplan.sql"
  "$PROJECT_ROOT/schemas/036_fable_uiux_handoff_package.sql"
  "$PROJECT_ROOT/schemas/037_fable_design_output_review.sql"
  "$PROJECT_ROOT/schemas/038_dlf_wix_staging_site_plan.sql"
  "$PROJECT_ROOT/schemas/039_dlf_wix_staging_build_tracking.sql"
  "$PROJECT_ROOT/schemas/040_wix_api_permission_capability_map.sql"
  "$PROJECT_ROOT/schemas/041_dlf_wix_ai_build_execution_plan.sql"
  "$PROJECT_ROOT/schemas/042_dlf_wix_ai_implementation_route_review.sql"
  "$PROJECT_ROOT/schemas/043_dlf_wix_setup_availability_check.sql"
  "$PROJECT_ROOT/schemas/044_import_jobs.sql"
  "$PROJECT_ROOT/schemas/045_whatsapp_assisted_outreach_activity.sql"
  "$PROJECT_ROOT/schemas/046_contact_groups_outreach.sql"
  "$PROJECT_ROOT/schemas/047_unit_registration_foundation.sql"
  "$PROJECT_ROOT/schemas/048_unit_ownership_tenancy_timeline.sql"
  "$PROJECT_ROOT/schemas/049_building_registration_readiness.sql"
  "$PROJECT_ROOT/schemas/050_registration_party_detail.sql"
  "$PROJECT_ROOT/schemas/051_registration_qa_dashboard.sql"
)

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  echo "Create it from docker/.env.example before applying the schema."
  exit 1
fi

for schema_file in "${SCHEMA_FILES[@]}"; do
  if [ ! -f "$schema_file" ]; then
    echo "Missing $schema_file"
    exit 1
  fi
done

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

echo "Applying schema to database: $POSTGRES_DB"

for schema_file in "${SCHEMA_FILES[@]}"; do
  echo "Applying $(basename "$schema_file")"
  "$DOCKER_BIN" exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
    < "$schema_file"
done

echo "Schema apply completed."
