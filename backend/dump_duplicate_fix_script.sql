SET search_path TO marketplace, public;

SELECT COUNT(*) FROM cars;

SELECT column_name FROM information_schema.columns
WHERE table_name = 'cars';

DELETE FROM cars
WHERE car_ad_id IS NOT NULL AND ctid NOT IN (
    SELECT MIN(ctid)
    FROM cars
    WHERE car_ad_id IS NOT NULL
    GROUP BY car_ad_id
);

SELECT COUNT(*) FROM cars;