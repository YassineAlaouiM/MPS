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

-- Machines Table
CREATE TABLE IF NOT EXISTS machines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status ENUM('operational', 'broken') NOT NULL DEFAULT 'operational',
    type BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Operators Table
CREATE TABLE IF NOT EXISTS operators (
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    arabic_name VARCHAR(100) NOT NULL,
    status ENUM('active', 'inactive', 'absent') NOT NULL DEFAULT 'active',
    last_shift_id INT DEFAULT NULL,
    FOREIGN KEY (last_shift_id) REFERENCES shifts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    week_number INT NOT NULL,
    year INT NOT NULL,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    FOREIGN KEY (operator_id) REFERENCES operators(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (production_id) REFERENCES production(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
