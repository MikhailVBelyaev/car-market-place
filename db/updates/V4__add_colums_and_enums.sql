-- This script adds new columns and enums to the marketplace.cars table
DO $$
BEGIN
  CREATE TYPE gear_enum AS ENUM ('AT', 'MT', 'DSG', 'CVT');
EXCEPTION WHEN duplicate_object THEN null;
END$$;

DO $$
BEGIN
  CREATE TYPE vehicle_type_enum AS ENUM ('EV', 'Fuel', 'Hybrid');
EXCEPTION WHEN duplicate_object THEN null;
END$$;

DO $$
BEGIN
  CREATE TYPE fuel_type_enum AS ENUM ('Petrol', 'Diesel', 'Electric', 'Gas');
EXCEPTION WHEN duplicate_object THEN null;
END$$;

DO $$
BEGIN
  CREATE TYPE condition_enum AS ENUM ('Ideal', 'Damaged', 'Needs Repair', 'Used');
EXCEPTION WHEN duplicate_object THEN null;
END$$;

ALTER TABLE marketplace.cars
ADD COLUMN IF NOT EXISTS gear_type gear_enum,
ADD COLUMN IF NOT EXISTS vehicle_type vehicle_type_enum,
ADD COLUMN IF NOT EXISTS fuel_type fuel_type_enum,
ADD COLUMN IF NOT EXISTS condition condition_enum,
ADD COLUMN IF NOT EXISTS customs_cleared BOOLEAN,
ADD COLUMN IF NOT EXISTS extras TEXT,
ADD COLUMN IF NOT EXISTS location TEXT;
