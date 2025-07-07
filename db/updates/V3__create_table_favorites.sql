CREATE TABLE IF NOT EXISTS marketplace.favorites (
    favorite_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES marketplace.users(user_id) ON DELETE CASCADE,
    car_id INT REFERENCES marketplace.cars(car_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);