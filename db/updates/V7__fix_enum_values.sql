-- Add new values to fuel_type_enum
DO $$ BEGIN
  ALTER TYPE marketplace.fuel_type_enum ADD VALUE IF NOT EXISTS 'Gasoline';
  ALTER TYPE marketplace.fuel_type_enum ADD VALUE IF NOT EXISTS 'Hybrid';
END $$;

-- Add new values to condition_enum
DO $$ BEGIN
  ALTER TYPE marketplace.condition_enum ADD VALUE IF NOT EXISTS 'ideal';
  ALTER TYPE marketplace.condition_enum ADD VALUE IF NOT EXISTS 'damaged';
  ALTER TYPE marketplace.condition_enum ADD VALUE IF NOT EXISTS 'needs_repair';
  ALTER TYPE marketplace.condition_enum ADD VALUE IF NOT EXISTS 'repaired';
END $$;
