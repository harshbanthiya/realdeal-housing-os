CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS contacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buildings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  developer text,
  project_name text,
  address_line_1 text,
  address_line_2 text,
  locality text,
  city text NOT NULL DEFAULT 'Mumbai',
  state text NOT NULL DEFAULT 'Maharashtra',
  postal_code text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inventory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_type text NOT NULL,
  channel text NOT NULL,
  title text,
  body text,
  status text NOT NULL DEFAULT 'draft',
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
  updated_at timestamptz NOT NULL DEFAULT now()
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
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  content_item_id uuid REFERENCES content_items(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  assigned_to text,
  status text NOT NULL DEFAULT 'open',
  priority text NOT NULL DEFAULT 'normal',
  due_at timestamptz,
  completed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contacts_phone_primary ON contacts(phone_primary);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_type_status ON contacts(contact_type, status);
CREATE INDEX IF NOT EXISTS idx_buildings_locality ON buildings(locality);
CREATE INDEX IF NOT EXISTS idx_inventory_building_id ON inventory(building_id);
CREATE INDEX IF NOT EXISTS idx_inventory_owner_contact_id ON inventory(owner_contact_id);
CREATE INDEX IF NOT EXISTS idx_inventory_availability_status ON inventory(availability_status);
CREATE INDEX IF NOT EXISTS idx_media_assets_inventory_id ON media_assets(inventory_id);
CREATE INDEX IF NOT EXISTS idx_content_items_status_channel ON content_items(status, channel);
CREATE INDEX IF NOT EXISTS idx_interactions_contact_occurred ON interactions(contact_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status_due_at ON tasks(status, due_at);

CREATE TRIGGER trg_contacts_updated_at
BEFORE UPDATE ON contacts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_buildings_updated_at
BEFORE UPDATE ON buildings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_inventory_updated_at
BEFORE UPDATE ON inventory
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_media_assets_updated_at
BEFORE UPDATE ON media_assets
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_content_items_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_interactions_updated_at
BEFORE UPDATE ON interactions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

