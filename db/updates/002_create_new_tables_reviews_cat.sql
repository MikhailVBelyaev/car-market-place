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