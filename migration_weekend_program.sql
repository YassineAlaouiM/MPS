-- Weekend Program migration
-- Separate tables extending the production schedule (schedule table unchanged).

USE schedule_management;

CREATE TABLE IF NOT EXISTS weekend_program (
    id INT AUTO_INCREMENT PRIMARY KEY,
    week_number INT NOT NULL,
    year INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_weekend_week (week_number, year)
);

CREATE TABLE IF NOT EXISTS weekend_schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    week_number INT NOT NULL,
    year INT NOT NULL,
    day ENUM('saturday', 'sunday') NOT NULL,
    machine_id INT NOT NULL,
    production_id INT NOT NULL,
    operator_id INT NOT NULL,
    shift_id INT NOT NULL,
    position INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (production_id) REFERENCES production(id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE,
    FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
    INDEX idx_weekend_lookup (week_number, year, day),
    INDEX idx_weekend_machine (week_number, year, day, machine_id, production_id)
);

CREATE TABLE IF NOT EXISTS weekend_cleared_machines (
    week_number INT NOT NULL,
    year INT NOT NULL,
    day ENUM('saturday', 'sunday') NOT NULL,
    machine_id INT NOT NULL,
    production_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (week_number, year, day, machine_id, production_id),
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (production_id) REFERENCES production(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weekend_visible_machines (
    week_number INT NOT NULL,
    year INT NOT NULL,
    day ENUM('saturday', 'sunday') NOT NULL,
    machine_id INT NOT NULL,
    production_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (week_number, year, day, machine_id, production_id),
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (production_id) REFERENCES production(id) ON DELETE CASCADE
);
