-- Migration script to update old database to match schema.sql
-- Run this on your server to migrate from old.sql to schema.sql structure

USE schedule_management;

-- =====================================================
-- STEP 1: Add missing columns to existing tables
-- =====================================================

-- Add poste_id to machines table if it doesn't exist
ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS poste_id INT,
ADD CONSTRAINT fk_machines_poste 
FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE SET NULL;

-- Add arabic_name to operators table if it doesn't exist
ALTER TABLE operators 
ADD COLUMN IF NOT EXISTS arabic_name VARCHAR(100) NOT NULL DEFAULT '';

-- Add last_shift_id to operators table if it doesn't exist
ALTER TABLE operators 
ADD COLUMN IF NOT EXISTS last_shift_id INT DEFAULT NULL,
ADD CONSTRAINT fk_operators_last_shift 
FOREIGN KEY (last_shift_id) REFERENCES shifts(id);

-- Add other_competences to operators table if it doesn't exist
ALTER TABLE operators 
ADD COLUMN IF NOT EXISTS other_competences TEXT;

-- Add status to operators table if it doesn't exist
ALTER TABLE operators 
ADD COLUMN IF NOT EXISTS status ENUM('active', 'inactive', 'absent') NOT NULL DEFAULT 'active';

-- Add created_at to operators table if it doesn't exist
ALTER TABLE operators 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to machines table if it doesn't exist
ALTER TABLE machines 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to shifts table if it doesn't exist
ALTER TABLE shifts 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to postes table if it doesn't exist
ALTER TABLE postes 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to absences table if it doesn't exist
ALTER TABLE absences 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to production table if it doesn't exist
ALTER TABLE production 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to schedule table if it doesn't exist
ALTER TABLE schedule 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to schedule_history table if it doesn't exist
ALTER TABLE schedule_history 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add created_at to articles table if it doesn't exist
ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- =====================================================
-- STEP 2: Create missing tables
-- =====================================================

-- Create operator_postes table if it doesn't exist
CREATE TABLE IF NOT EXISTS operator_postes (
    op_id INT NOT NULL,
    poste_id INT NOT NULL,
    PRIMARY KEY (op_id, poste_id),
    FOREIGN KEY (op_id) REFERENCES operators(id) ON DELETE CASCADE,
    FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE CASCADE
);

-- Create user_accessible_pages table if it doesn't exist
CREATE TABLE IF NOT EXISTS user_accessible_pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    page_name VARCHAR(50) NOT NULL,
    can_edit BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_page (user_id, page_name)
);

-- Create daily_schedule_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS daily_schedule_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_recorded DATE NOT NULL,
    week_number INT NOT NULL,
    year INT NOT NULL,
    machine_id INT,
    production_id INT,
    status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
    operator_id INT,
    shift_id INT,
    position INT NOT NULL DEFAULT 1,
    machine_name VARCHAR(100),
    operator_name VARCHAR(100),
    shift_name VARCHAR(50),
    shift_start_time TIME,
    shift_end_time TIME,
    article_name VARCHAR(255),
    article_abbreviation VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (operator_id) REFERENCES operators(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (production_id) REFERENCES production(id),
    INDEX idx_date_recorded (date_recorded),
    INDEX idx_week_year (week_number, year),
    UNIQUE KEY unique_daily_assignment (date_recorded, machine_id, production_id, operator_id, shift_id, position)
);

-- Create operator_rest_days table if it doesn't exist
CREATE TABLE IF NOT EXISTS operator_rest_days (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operator_id INT NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
);

-- Create history_nfm table if it doesn't exist
CREATE TABLE IF NOT EXISTS history_nfm (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT NOT NULL,
    issue TEXT,
    reported_date DATETIME NOT NULL,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- Create completed_productions table if it doesn't exist
CREATE TABLE IF NOT EXISTS completed_productions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    production_id INT NOT NULL,
    machine_id INT NOT NULL,
    machine_name VARCHAR(100) NOT NULL,
    article_id INT,
    article_name VARCHAR(255),
    article_abbreviation VARCHAR(20),
    operator_id INT,
    operator_name VARCHAR(100),
    shift_id INT,
    shift_name VARCHAR(50),
    shift_start_time TIME,
    shift_end_time TIME,
    position INT DEFAULT 1,
    week_number INT NOT NULL,
    year INT NOT NULL,
    completion_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (production_id) REFERENCES production(id),
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (operator_id) REFERENCES operators(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id)
);

-- =====================================================
-- STEP 3: Add missing indexes and constraints
-- =====================================================

-- Add indexes to daily_schedule_history if they don't exist
CREATE INDEX IF NOT EXISTS idx_date_recorded ON daily_schedule_history(date_recorded);
CREATE INDEX IF NOT EXISTS idx_week_year ON daily_schedule_history(week_number, year);

-- =====================================================
-- STEP 4: Insert default postes data
-- =====================================================

INSERT INTO postes (name, type) VALUES
    ('machine', 'machine'),
    ('laveuse', 'machine'),
    ('extrudeuse', 'machine'),
    ('broyeur', 'machine'),
    ('melange', 'service'),
    ('services', 'service'),
    ('chargement', 'service'),
    ('emballage', 'service')
ON DUPLICATE KEY UPDATE name=name;

-- =====================================================
-- STEP 5: Update existing data if needed
-- =====================================================

-- Update operators to have arabic_name if it's empty
UPDATE operators SET arabic_name = name WHERE arabic_name = '' OR arabic_name IS NULL;

-- Update operators to have status if it's not set
UPDATE operators SET status = 'active' WHERE status IS NULL;

-- =====================================================
-- STEP 6: Verify migration
-- =====================================================

-- Show all tables to verify they exist
SHOW TABLES;

-- Show table structures to verify columns
DESCRIBE machines;
DESCRIBE operators;
DESCRIBE production;
DESCRIBE schedule;
DESCRIBE daily_schedule_history;

-- Migration completed! 