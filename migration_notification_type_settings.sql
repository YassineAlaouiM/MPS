-- Per-admin notification email preferences (in-app notifications are always created)

USE schedule_management;

DROP TABLE IF EXISTS notification_type_settings;

CREATE TABLE IF NOT EXISTS user_notification_email_preferences (
    user_id INT NOT NULL,
    type VARCHAR(50) NOT NULL,
    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

INSERT IGNORE INTO user_notification_email_preferences (user_id, type, email_enabled)
SELECT u.id, t.type, TRUE
FROM users u
CROSS JOIN (
    SELECT 'nfm_reported' AS type UNION ALL
    SELECT 'nfm_fixed' UNION ALL
    SELECT 'absence_created' UNION ALL
    SELECT 'schedule_confirmed' UNION ALL
    SELECT 'weekend_confirmed' UNION ALL
    SELECT 'rest_days_updated'
) t
WHERE u.role = 'admin';
