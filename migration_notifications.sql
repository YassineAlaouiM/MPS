-- Notifications migration (admin-wide, one row per event)

USE schedule_management;

DROP TABLE IF EXISTS notifications;

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    notification_date DATE NOT NULL,
    notification_time TIME NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    email_status ENUM('pending', 'sent', 'failed', 'skipped') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_unread (is_read),
    INDEX idx_created (created_at),
    INDEX idx_type (type)
);
