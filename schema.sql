CREATE DATABASE IF NOT EXISTS schedule_management;
USE schedule_management;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shifts Table
CREATE TABLE IF NOT EXISTS shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Postes Table
CREATE TABLE IF NOT EXISTS postes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Machines Table
CREATE TABLE IF NOT EXISTS machines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status ENUM('operational', 'broken') NOT NULL DEFAULT 'operational',
    type BOOLEAN DEFAULT FALSE,
    poste_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE SET NULL
);

-- Operators Table
CREATE TABLE IF NOT EXISTS operators (
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    arabic_name VARCHAR(100) NOT NULL,
    status ENUM('active', 'inactive', 'absent') NOT NULL DEFAULT 'active',
    last_shift_id INT DEFAULT NULL,
    other_competences TEXT,
    FOREIGN KEY (last_shift_id) REFERENCES shifts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Operator Postes Table (Many-to-Many Relationship)
CREATE TABLE IF NOT EXISTS operator_postes (
    op_id INT NOT NULL,
    poste_id INT NOT NULL,
    PRIMARY KEY (op_id, poste_id),
    FOREIGN KEY (op_id) REFERENCES operators(id) ON DELETE CASCADE,
    FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE CASCADE
);

-- Absences Table
CREATE TABLE IF NOT EXISTS absences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operator_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    FOREIGN KEY (operator_id) REFERENCES operators(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Non-Functioning Machines Table
CREATE TABLE IF NOT EXISTS non_functioning_machines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT NOT NULL,
    issue TEXT,
    reported_date DATETIME NOT NULL,
    fixed_date DATETIME,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- Articles Table
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    abbreviation VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Production Table
CREATE TABLE IF NOT EXISTS production (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT NOT NULL,
    article_id INT NULL, 
    quantity INT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    hour_start TIME NULL,
    hour_end TIME NULL,
    status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

-- Schedule Table
CREATE TABLE IF NOT EXISTS schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT,
    production_id INT,
    operator_id INT,
    shift_id INT,
    position INT NOT NULL DEFAULT 1,
    week_number INT NOT NULL,
    year INT NOT NULL,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (operator_id) REFERENCES operators(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (production_id) REFERENCES production(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schedule History Table
CREATE TABLE IF NOT EXISTS schedule_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    machine_id INT NOT NULL,
    machine_name VARCHAR(255) NOT NULL,
    shift_id INT NOT NULL,
    shift_name VARCHAR(255) NOT NULL,
    shift_start_time TIME NOT NULL,
    shift_end_time TIME NOT NULL,
    operator_id INT,
    operator_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (operator_id) REFERENCES operators(id)
);

-- User Accessible Pages Table
CREATE TABLE IF NOT EXISTS user_accessible_pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    page_name VARCHAR(50) NOT NULL,
    can_edit BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_page (user_id, page_name)
);

-- Daily Schedule History Table
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

-- Operator Rest Days Table
CREATE TABLE IF NOT EXISTS operator_rest_days (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operator_id INT NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
);

-- History NFM Table
CREATE TABLE IF NOT EXISTS history_nfm (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT NOT NULL,
    issue TEXT,
    reported_date DATETIME NOT NULL,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- Completed Productions Table
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

-- Insert default postes data
-- INSERT INTO postes (name, type) VALUES
--     ('machine', 'machine'),
--     ('laveuse', 'machine'),
--     ('extrudeuse', 'machine'),
--     ('broyeur', 'machine'),
--     ('melange', 'service'),
--     ('services', 'service'),
--     ('chargement', 'service'),
--     ('emballage', 'service')
-- ON DUPLICATE KEY UPDATE name=name;
