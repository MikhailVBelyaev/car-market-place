-- Add new values to fuel_type_enum
DO $$ BEGIN
  ALTER TYPE fuel_type_enum ADD VALUE IF NOT EXISTS 'Gasoline';
  ALTER TYPE fuel_type_enum ADD VALUE IF NOT EXISTS 'Hybrid';
END $$;

-- Add new values to condition_enum
DO $$ BEGIN
  ALTER TYPE condition_enum ADD VALUE IF NOT EXISTS 'ideal';
  ALTER TYPE condition_enum ADD VALUE IF NOT EXISTS 'damaged';
  ALTER TYPE condition_enum ADD VALUE IF NOT EXISTS 'needs_repair';
  ALTER TYPE condition_enum ADD VALUE IF NOT EXISTS 'repaired';
END $$;

-- Update existing rows to match new values
UPDATE marketplace.cars SET fuel_type = 'Gasoline' WHERE fuel_type = 'Petrol';
UPDATE marketplace.cars SET fuel_type = 'Hybrid' WHERE fuel_type = 'Electric'; -- If this applies

UPDATE marketplace.cars SET condition = 'ideal' WHERE condition = 'Ideal';
UPDATE marketplace.cars SET condition = 'damaged' WHERE condition = 'Damaged';
UPDATE marketplace.cars SET condition = 'needs_repair' WHERE condition = 'Needs Repair';
UPDATE marketplace.cars SET condition = 'repaired' WHERE condition = 'Used'; -- if 'Used' means repaired

-- Optionally: drop old enum values (PostgreSQL 13+ only!)
ALTER TYPE fuel_type_enum DROP VALUE 'Petrol';
ALTER TYPE condition_enum DROP VALUE 'Ideal';
