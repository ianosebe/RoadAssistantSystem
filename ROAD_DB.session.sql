-- 1. Create the Database
CREATE DATABASE IF NOT EXISTS road_assist_db;
USE road_assist_db;

-- 2. Create the Users Table
-- This stores Drivers, Mechanics, and Admins. 
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('driver', 'mechanic', 'admin') NOT NULL,
    vehicle_details VARCHAR(100) DEFAULT NULL, -- Only used if role is 'driver'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create the Mechanic Profiles Table
-- Linked to the Users table. Stores data specific to mechanics.
CREATE TABLE mechanic_profiles (
    profile_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE, -- True when they toggle "Active" in the app
    current_lat DECIMAL(10, 8) DEFAULT NULL, -- GPS Latitude
    current_lng DECIMAL(11, 8) DEFAULT NULL, -- GPS Longitude
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. Create the Service Requests Table
-- This is the core table where the breakdowns and jobs are tracked.
CREATE TABLE service_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NOT NULL,
    mechanic_id INT DEFAULT NULL, -- Starts as NULL until a mechanic accepts
    problem_type VARCHAR(50) NOT NULL, -- e.g., 'Flat Tire', 'Dead Battery'
    status ENUM('pending', 'accepted', 'completed') DEFAULT 'pending',
    location_lat DECIMAL(10, 8) NOT NULL,
    location_lng DECIMAL(11, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_id) REFERENCES users(user_id) ON DELETE SET NULL
);

INSERT INTO users (full_name, phone_number, password_hash, role, vehicle_details)
VALUES ('Ian Nyangau', '0712345678', 'hashed_password_here', 'driver', 'Toyota Corolla');


INSERT INTO users (full_name, phone_number, password_hash, role)
VALUES ('Dickson Mechanic', '0798765432', 'hashed_password_here', 'mechanic');

-- Assuming the user_id generated above was 2:
INSERT INTO mechanic_profiles (user_id, specialization, is_active)
VALUES (2, 'Engine Repair', FALSE);

INSERT INTO service_requests (driver_id, problem_type, location_lat, location_lng)
VALUES (1, 'Flat Tire', -1.286389, 36.817223); -- Example coordinates for Nairobi


SELECT users.full_name, users.phone_number, mechanic_profiles.specialization, mechanic_profiles.current_lat, mechanic_profiles.current_lng
FROM mechanic_profiles
JOIN users ON mechanic_profiles.user_id = users.user_id
WHERE mechanic_profiles.is_active = TRUE 
AND mechanic_profiles.current_lat IS NOT NULL;

-- Assuming mechanic's user_id is 2, and the request_id is 1
UPDATE service_requests 
SET mechanic_id = 2, status = 'accepted'
WHERE request_id = 1 AND status = 'pending'; 
-- The "AND status = 'pending'" part is the safety lock to ensure it hasn't already been claimed!

-- Get Total Registered Drivers
SELECT COUNT(*) AS total_drivers FROM users WHERE role = 'driver';

-- Get Total Registered Mechanics
SELECT COUNT(*) AS total_mechanics FROM users WHERE role = 'mechanic';

-- Get Total Active/Pending Requests
SELECT COUNT(*) AS active_requests FROM service_requests WHERE status IN ('pending', 'accepted');

-- Get Total Completed Jobs
SELECT COUNT(*) AS completed_jobs FROM service_requests WHERE status = 'completed';