-- Check if schema exists and drop it if needed (optional, be cautious in production)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'marketplace') THEN
        RAISE NOTICE 'Dropping schema marketplace...';
        EXECUTE 'DROP SCHEMA marketplace CASCADE';
    END IF;
END $$;

-- Create the schema if it does not exist
CREATE SCHEMA IF NOT EXISTS marketplace;

-- Switch to the marketplace schema
SET search_path TO marketplace;

-- Check if tables exist and drop them if needed
DROP TABLE IF EXISTS cars CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
-- Add other tables as needed

-- Create the cars table
CREATE TABLE IF NOT EXISTS cars (
    car_id SERIAL PRIMARY KEY,
    brand VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    year INT CHECK (year > 1900),
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    car_id INT REFERENCES cars(car_id) ON DELETE CASCADE,
    buyer_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_amount DECIMAL(10, 2) NOT NULL
);

-- Example of altering a table to add a new column if it does not exist
ALTER TABLE cars ADD COLUMN IF NOT EXISTS odometer INT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

-- You can continue to add more tables and alter statements here as needed...

-- Example: Adding a new table for user reviews of cars
CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    car_id INT REFERENCES cars(car_id) ON DELETE CASCADE,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example: Creating a table for car categories (e.g., sedan, SUV, etc.)
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) UNIQUE NOT NULL
);

-- Example: Associating cars with categories (many-to-many relationship)
CREATE TABLE IF NOT EXISTS car_categories (
    car_id INT REFERENCES cars(car_id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(category_id) ON DELETE CASCADE,
    PRIMARY KEY (car_id, category_id)
);