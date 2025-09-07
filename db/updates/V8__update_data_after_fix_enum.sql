
-- Update existing rows to match new values
UPDATE marketplace.cars SET fuel_type = 'Gasoline' WHERE fuel_type = 'Petrol';
UPDATE marketplace.cars SET fuel_type = 'Hybrid' WHERE fuel_type = 'Electric'; -- If this applies

UPDATE marketplace.cars SET condition = 'ideal' WHERE condition = 'Ideal';
UPDATE marketplace.cars SET condition = 'damaged' WHERE condition = 'Damaged';
UPDATE marketplace.cars SET condition = 'needs_repair' WHERE condition = 'Needs Repair';
UPDATE marketplace.cars SET condition = 'repaired' WHERE condition = 'Used';