-- Holiday Program migration (Jours fériés)
-- Date-keyed overlay with highest priority over weekend and weekday programs.

USE schedule_management;

CREATE TABLE IF NOT EXISTS holiday_program (
    id INT AUTO_INCREMENT PRIMARY KEY,
    holiday_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_holiday_date (holiday_date)
);

CREATE TABLE IF NOT EXISTS holiday_schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    holiday_date DATE NOT NULL,
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
    INDEX idx_holiday_lookup (holiday_date),
    INDEX idx_holiday_machine (holiday_date, machine_id, production_id)
);

CREATE TABLE IF NOT EXISTS holiday_cleared_machines (
    holiday_date DATE NOT NULL,
    machine_id INT NOT NULL,
    production_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (holiday_date, machine_id, production_id),
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (production_id) REFERENCES production(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS holiday_visible_machines (
    holiday_date DATE NOT NULL,
    machine_id INT NOT NULL,
    production_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (holiday_date, machine_id, production_id),
    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
    FOREIGN KEY (production_id) REFERENCES production(id) ON DELETE CASCADE
);
