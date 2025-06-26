


ALTER TABLE marketplace.cars
ADD COLUMN owner_type VARCHAR(100),
ADD COLUMN body_type VARCHAR(100),
ADD COLUMN owner_count VARCHAR(10),
ADD COLUMN owner_name VARCHAR(255),
ADD COLUMN owner_member_since VARCHAR(100),
ADD COLUMN owner_last_seen VARCHAR(100),
ADD COLUMN owner_profile_url TEXT,
ADD COLUMN owner_tel_number VARCHAR(20);

ALTER TABLE marketplace.cars
ADD COLUMN color VARCHAR(50);

ALTER TABLE marketplace.cars
ADD COLUMN customer_paid_tax BOOLEAN;

ALTER TABLE marketplace.cars
ADD COLUMN additional_options TEXT;


ALTER TABLE marketplace.cars
ADD COLUMN car_ad_id VARCHAR(50),
ADD COLUMN reference_url TEXT,
ADD COLUMN description_detail TEXT;