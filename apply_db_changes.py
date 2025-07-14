#!/usr/bin/env python3
"""
Script to apply database schema changes for the new postes structure.
This will create the new tables and remove the old postes column.
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Root.123'),
    'database': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def apply_schema_changes():
    """Apply the database schema changes"""
    connection = pymysql.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            print("Applying database schema changes...")
            
            # 1. Create postes table if it doesn't exist
            print("Creating postes table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS postes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. Create operator_postes table if it doesn't exist
            print("Creating operator_postes table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operator_postes (
                    op_id INT NOT NULL,
                    poste_id INT NOT NULL,
                    PRIMARY KEY (op_id, poste_id),
                    FOREIGN KEY (op_id) REFERENCES operators(id) ON DELETE CASCADE,
                    FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE CASCADE
                )
            """)
            
            # 3. Populate postes table with standard postes
            print("Populating postes table...")
            postes_data = [
                ('machine', 'machine'),
                ('laveuse', 'machine'),
                ('extrudeuse', 'machine'),
                ('broyeur', 'machine'),
                ('melange', 'service'),
                ('services', 'service'),
                ('chargement', 'service'),
                ('emballage', 'service')
            ]
            
            for name, type_val in postes_data:
                cursor.execute(
                    "INSERT INTO postes (name, type) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=name",
                    (name, type_val)
                )
            
            # 4. Check if postes column exists in operators table
            cursor.execute("SHOW COLUMNS FROM operators LIKE 'postes'")
            postes_column_exists = cursor.fetchone()
            
            if postes_column_exists:
                print("Postes column exists. Migrating data before removing...")
                
                # Get all operators with postes data
                cursor.execute("SELECT id, name, postes FROM operators WHERE postes IS NOT NULL AND postes != ''")
                operators = cursor.fetchall()
                
                print(f"Found {len(operators)} operators with postes data")
                
                # Get all available postes
                cursor.execute("SELECT id, name FROM postes")
                postes = {p['name']: p['id'] for p in cursor.fetchall()}
                
                # Migrate data
                for operator in operators:
                    operator_id = operator['id']
                    postes_string = operator['postes']
                    
                    # Parse the comma-separated postes string
                    poste_names = [p.strip().lower() for p in postes_string.split(',') if p.strip()]
                    
                    # Find matching poste IDs and insert into operator_postes
                    for poste_name in poste_names:
                        if poste_name in postes:
                            cursor.execute(
                                "INSERT IGNORE INTO operator_postes (op_id, poste_id) VALUES (%s, %s)",
                                (operator_id, postes[poste_name])
                            )
                            print(f"Migrated poste '{poste_name}' for operator {operator['name']}")
                        else:
                            print(f"Warning: Poste '{poste_name}' not found for operator {operator['name']}")
                
                # 5. Remove the postes column from operators table
                print("Removing postes column from operators table...")
                cursor.execute("ALTER TABLE operators DROP COLUMN postes")
                print("Postes column removed successfully!")
            else:
                print("Postes column does not exist. Skipping migration.")
            
            connection.commit()
            print("Database schema changes applied successfully!")
            
    except Exception as e:
        print(f"Error applying schema changes: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    print("Starting database schema changes...")
    apply_schema_changes()
    print("Schema changes completed!") 