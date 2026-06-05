CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS import_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name text NOT NULL,
  source_type text NOT NULL DEFAULT 'other',
  source_file_path text,
  uploaded_by text,
  status text NOT NULL DEFAULT 'planned',
  total_rows integer NOT NULL DEFAULT 0,
  processed_rows integer NOT NULL DEFAULT 0,
  error_rows integer NOT NULL DEFAULT 0,
  started_at timestamptz,
  completed_at timestamptz,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT import_batches_source_type_check
    CHECK (source_type IN ('contacts', 'buildings', 'inventory', 'media', 'content', 'interactions', 'tasks', 'mixed', 'other')),
  CONSTRAINT import_batches_status_check
    CHECK (status IN ('planned', 'importing', 'completed', 'failed', 'rolled_back'))
);

CREATE TABLE IF NOT EXISTS contacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  full_name text NOT NULL,
  contact_type text NOT NULL DEFAULT 'lead',
  company_name text,
  phone_primary text,
  phone_secondary text,
  whatsapp_number text,
  email text,
  source text,
  status text NOT NULL DEFAULT 'active',
  tags text[] NOT NULL DEFAULT '{}',
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contacts_contact_type_check
    CHECK (contact_type IN ('lead', 'client', 'owner', 'buyer', 'seller', 'tenant', 'agent', 'developer', 'vendor', 'other')),
  CONSTRAINT contacts_status_check
    CHECK (status IN ('new', 'active', 'inactive', 'do_not_contact', 'duplicate', 'archived'))
);

CREATE TABLE IF NOT EXISTS buildings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  name text NOT NULL,
  developer text,
  project_name text,
  address_line_1 text,
  address_line_2 text,
  area text,
  locality text,
  city text NOT NULL DEFAULT 'Mumbai',
  state text NOT NULL DEFAULT 'Maharashtra',
  postal_code text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inventory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  owner_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  unit_number text,
  listing_type text NOT NULL DEFAULT 'sale',
  property_type text NOT NULL DEFAULT 'apartment',
  bedrooms numeric(4,1),
  bathrooms numeric(4,1),
  carpet_area_sq_ft integer,
  built_up_area_sq_ft integer,
  floor_number integer,
  total_floors integer,
  parking_count integer,
  facing text,
  furnishing_status text,
  availability_status text NOT NULL DEFAULT 'available',
  asking_price numeric(14,2),
  monthly_rent numeric(14,2),
  deposit_amount numeric(14,2),
  maintenance_amount numeric(14,2),
  internal_notes text,
  public_description text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT inventory_listing_type_check
    CHECK (listing_type IN ('sale', 'rent', 'lease', 'sale_or_rent')),
  CONSTRAINT inventory_property_type_check
    CHECK (property_type IN ('apartment', 'villa', 'office', 'shop', 'commercial', 'plot', 'other')),
  CONSTRAINT inventory_availability_status_check
    CHECK (availability_status IN ('available', 'blocked', 'sold', 'rented', 'inactive', 'draft', 'unknown'))
);

CREATE TABLE IF NOT EXISTS media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  file_path text NOT NULL,
  media_type text NOT NULL,
  title text,
  caption text,
  status text NOT NULL DEFAULT 'raw',
  sha256_hash text,
  file_size_bytes bigint,
  width_px integer,
  height_px integer,
  duration_seconds numeric(10,2),
  taken_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT media_assets_media_type_check
    CHECK (media_type IN ('photo', 'video', 'floor_plan', 'document', 'other')),
  CONSTRAINT media_assets_status_check
    CHECK (status IN ('raw', 'editing', 'ready', 'approved', 'published', 'archived'))
);

CREATE TABLE IF NOT EXISTS content_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_type text NOT NULL,
  channel text NOT NULL,
  title text,
  body text,
  status text NOT NULL DEFAULT 'draft',
  approval_status text NOT NULL DEFAULT 'pending',
  approval_notes text,
  approved_by text,
  approved_at timestamptz,
  scheduled_for timestamptz,
  published_at timestamptz,
  published_url text,
  related_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  media_asset_id uuid REFERENCES media_assets(id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT content_items_content_type_check
    CHECK (content_type IN ('listing_caption', 'wix_listing', 'social_post', 'email', 'whatsapp', 'youtube_description', 'blog', 'seo_meta', 'other')),
  CONSTRAINT content_items_channel_check
    CHECK (channel IN ('wix', 'instagram', 'facebook', 'linkedin', 'youtube', 'email', 'whatsapp', 'internal', 'other')),
  CONSTRAINT content_items_status_check
    CHECK (status IN ('draft', 'in_review', 'approved', 'scheduled', 'published', 'rejected', 'archived')),
  CONSTRAINT content_items_approval_status_check
    CHECK (approval_status IN ('not_required', 'pending', 'approved', 'rejected', 'changes_requested'))
);

CREATE TABLE IF NOT EXISTS interactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  channel text NOT NULL,
  direction text NOT NULL DEFAULT 'outbound',
  occurred_at timestamptz NOT NULL DEFAULT now(),
  summary text NOT NULL,
  outcome text,
  next_follow_up_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT interactions_channel_check
    CHECK (channel IN ('phone', 'whatsapp', 'email', 'meeting', 'site_visit', 'social', 'wix', 'nocodb', 'n8n', 'other')),
  CONSTRAINT interactions_direction_check
    CHECK (direction IN ('inbound', 'outbound', 'internal'))
);

CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  content_item_id uuid REFERENCES content_items(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  task_type text NOT NULL DEFAULT 'follow_up',
  assigned_to text,
  status text NOT NULL DEFAULT 'open',
  priority text NOT NULL DEFAULT 'normal',
  due_at timestamptz,
  follow_up_at timestamptz,
  completed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT tasks_task_type_check
    CHECK (task_type IN ('follow_up', 'site_visit', 'content', 'import', 'admin', 'other')),
  CONSTRAINT tasks_status_check
    CHECK (status IN ('open', 'in_progress', 'waiting', 'completed', 'cancelled')),
  CONSTRAINT tasks_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS import_batch_id uuid;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE buildings ADD COLUMN IF NOT EXISTS import_batch_id uuid;
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS area text;
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE inventory ADD COLUMN IF NOT EXISTS import_batch_id uuid;
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS import_batch_id uuid;

ALTER TABLE content_items ADD COLUMN IF NOT EXISTS approval_status text NOT NULL DEFAULT 'pending';

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS building_id uuid;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_type text NOT NULL DEFAULT 'follow_up';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS follow_up_at timestamptz;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'contacts_import_batch_id_fkey') THEN
    ALTER TABLE contacts
      ADD CONSTRAINT contacts_import_batch_id_fkey
      FOREIGN KEY (import_batch_id) REFERENCES import_batches(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'buildings_import_batch_id_fkey') THEN
    ALTER TABLE buildings
      ADD CONSTRAINT buildings_import_batch_id_fkey
      FOREIGN KEY (import_batch_id) REFERENCES import_batches(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'inventory_import_batch_id_fkey') THEN
    ALTER TABLE inventory
      ADD CONSTRAINT inventory_import_batch_id_fkey
      FOREIGN KEY (import_batch_id) REFERENCES import_batches(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'media_assets_import_batch_id_fkey') THEN
    ALTER TABLE media_assets
      ADD CONSTRAINT media_assets_import_batch_id_fkey
      FOREIGN KEY (import_batch_id) REFERENCES import_batches(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_building_id_fkey') THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_building_id_fkey
      FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE SET NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'contacts_contact_type_check') THEN
    ALTER TABLE contacts
      ADD CONSTRAINT contacts_contact_type_check
      CHECK (contact_type IN ('lead', 'client', 'owner', 'buyer', 'seller', 'tenant', 'agent', 'developer', 'vendor', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'contacts_status_check') THEN
    ALTER TABLE contacts
      ADD CONSTRAINT contacts_status_check
      CHECK (status IN ('new', 'active', 'inactive', 'do_not_contact', 'duplicate', 'archived')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'inventory_listing_type_check') THEN
    ALTER TABLE inventory
      ADD CONSTRAINT inventory_listing_type_check
      CHECK (listing_type IN ('sale', 'rent', 'lease', 'sale_or_rent')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'inventory_property_type_check') THEN
    ALTER TABLE inventory
      ADD CONSTRAINT inventory_property_type_check
      CHECK (property_type IN ('apartment', 'villa', 'office', 'shop', 'commercial', 'plot', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'inventory_availability_status_check') THEN
    ALTER TABLE inventory
      ADD CONSTRAINT inventory_availability_status_check
      CHECK (availability_status IN ('available', 'blocked', 'sold', 'rented', 'inactive', 'draft', 'unknown')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'media_assets_media_type_check') THEN
    ALTER TABLE media_assets
      ADD CONSTRAINT media_assets_media_type_check
      CHECK (media_type IN ('photo', 'video', 'floor_plan', 'document', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'media_assets_status_check') THEN
    ALTER TABLE media_assets
      ADD CONSTRAINT media_assets_status_check
      CHECK (status IN ('raw', 'editing', 'ready', 'approved', 'published', 'archived')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'content_items_content_type_check') THEN
    ALTER TABLE content_items
      ADD CONSTRAINT content_items_content_type_check
      CHECK (content_type IN ('listing_caption', 'wix_listing', 'social_post', 'email', 'whatsapp', 'youtube_description', 'blog', 'seo_meta', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'content_items_channel_check') THEN
    ALTER TABLE content_items
      ADD CONSTRAINT content_items_channel_check
      CHECK (channel IN ('wix', 'instagram', 'facebook', 'linkedin', 'youtube', 'email', 'whatsapp', 'internal', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'content_items_status_check') THEN
    ALTER TABLE content_items
      ADD CONSTRAINT content_items_status_check
      CHECK (status IN ('draft', 'in_review', 'approved', 'scheduled', 'published', 'rejected', 'archived')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'content_items_approval_status_check') THEN
    ALTER TABLE content_items
      ADD CONSTRAINT content_items_approval_status_check
      CHECK (approval_status IN ('not_required', 'pending', 'approved', 'rejected', 'changes_requested')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'interactions_channel_check') THEN
    ALTER TABLE interactions
      ADD CONSTRAINT interactions_channel_check
      CHECK (channel IN ('phone', 'whatsapp', 'email', 'meeting', 'site_visit', 'social', 'wix', 'nocodb', 'n8n', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'interactions_direction_check') THEN
    ALTER TABLE interactions
      ADD CONSTRAINT interactions_direction_check
      CHECK (direction IN ('inbound', 'outbound', 'internal')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_task_type_check') THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_task_type_check
      CHECK (task_type IN ('follow_up', 'site_visit', 'content', 'import', 'admin', 'other')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_status_check') THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_status_check
      CHECK (status IN ('open', 'in_progress', 'waiting', 'completed', 'cancelled')) NOT VALID;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_priority_check') THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_priority_check
      CHECK (priority IN ('low', 'normal', 'high', 'urgent')) NOT VALID;
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_import_batches_source_type ON import_batches(source_type);
CREATE INDEX IF NOT EXISTS idx_import_batches_status ON import_batches(status);
CREATE INDEX IF NOT EXISTS idx_import_batches_created_at ON import_batches(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_contacts_import_batch_id ON contacts(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_contacts_phone_primary ON contacts(phone_primary);
CREATE INDEX IF NOT EXISTS idx_contacts_phone_secondary ON contacts(phone_secondary);
CREATE INDEX IF NOT EXISTS idx_contacts_whatsapp_number ON contacts(whatsapp_number);
CREATE INDEX IF NOT EXISTS idx_contacts_email_lower ON contacts(lower(email));
CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
CREATE INDEX IF NOT EXISTS idx_contacts_type_status ON contacts(contact_type, status);

CREATE INDEX IF NOT EXISTS idx_buildings_import_batch_id ON buildings(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_buildings_name_lower ON buildings(lower(name));
CREATE INDEX IF NOT EXISTS idx_buildings_area ON buildings(area);
CREATE INDEX IF NOT EXISTS idx_buildings_locality ON buildings(locality);
CREATE INDEX IF NOT EXISTS idx_buildings_city_area ON buildings(city, area);

CREATE INDEX IF NOT EXISTS idx_inventory_import_batch_id ON inventory(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_inventory_building_id ON inventory(building_id);
CREATE INDEX IF NOT EXISTS idx_inventory_owner_contact_id ON inventory(owner_contact_id);
CREATE INDEX IF NOT EXISTS idx_inventory_availability_status ON inventory(availability_status);
CREATE INDEX IF NOT EXISTS idx_inventory_listing_type ON inventory(listing_type);
CREATE INDEX IF NOT EXISTS idx_inventory_building_status ON inventory(building_id, availability_status);

CREATE INDEX IF NOT EXISTS idx_media_assets_import_batch_id ON media_assets(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_inventory_id ON media_assets(inventory_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_building_id ON media_assets(building_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_status ON media_assets(status);
CREATE INDEX IF NOT EXISTS idx_media_assets_media_type ON media_assets(media_type);

CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status);
CREATE INDEX IF NOT EXISTS idx_content_items_approval_status ON content_items(approval_status);
CREATE INDEX IF NOT EXISTS idx_content_items_status_channel ON content_items(status, channel);
CREATE INDEX IF NOT EXISTS idx_content_items_building_id ON content_items(building_id);
CREATE INDEX IF NOT EXISTS idx_content_items_inventory_id ON content_items(inventory_id);
CREATE INDEX IF NOT EXISTS idx_content_items_scheduled_for ON content_items(scheduled_for);

CREATE INDEX IF NOT EXISTS idx_interactions_contact_id ON interactions(contact_id);
CREATE INDEX IF NOT EXISTS idx_interactions_contact_occurred ON interactions(contact_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_next_follow_up_at ON interactions(next_follow_up_at);
CREATE INDEX IF NOT EXISTS idx_interactions_channel ON interactions(channel);

CREATE INDEX IF NOT EXISTS idx_tasks_contact_id ON tasks(contact_id);
CREATE INDEX IF NOT EXISTS idx_tasks_building_id ON tasks(building_id);
CREATE INDEX IF NOT EXISTS idx_tasks_inventory_id ON tasks(inventory_id);
CREATE INDEX IF NOT EXISTS idx_tasks_content_item_id ON tasks(content_item_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_follow_up_at ON tasks(follow_up_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status_due_at ON tasks(status, due_at);

DROP TRIGGER IF EXISTS trg_import_batches_updated_at ON import_batches;
CREATE TRIGGER trg_import_batches_updated_at
BEFORE UPDATE ON import_batches
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_contacts_updated_at ON contacts;
CREATE TRIGGER trg_contacts_updated_at
BEFORE UPDATE ON contacts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_buildings_updated_at ON buildings;
CREATE TRIGGER trg_buildings_updated_at
BEFORE UPDATE ON buildings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_inventory_updated_at ON inventory;
CREATE TRIGGER trg_inventory_updated_at
BEFORE UPDATE ON inventory
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_media_assets_updated_at ON media_assets;
CREATE TRIGGER trg_media_assets_updated_at
BEFORE UPDATE ON media_assets
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_items_updated_at ON content_items;
CREATE TRIGGER trg_content_items_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_interactions_updated_at ON interactions;
CREATE TRIGGER trg_interactions_updated_at
BEFORE UPDATE ON interactions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON tasks;
CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
