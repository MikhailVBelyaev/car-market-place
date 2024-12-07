-- Example of altering a table to add a new column if it does not exist
ALTER TABLE cars ADD COLUMN IF NOT EXISTS mileage INT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);