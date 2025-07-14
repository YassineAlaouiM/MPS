#!/usr/bin/env python3
"""
Migration script to move operator postes from the old TEXT column to the new operator_postes table.
Run this after creating the new tables and populating the postes table.
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

def migrate_operator_postes():
    """Migrate operator postes from old column to new table"""
    connection = pymysql.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            # First, ensure postes table is populated
            print("Ensuring postes table is populated...")
            postes_data = [
                ('machine', 'machine'),
                ('laveuse', 'machine'),
                ('extrudeuse', 'machine'),
                ('broyeur', 'machine'),
                ('melange', 'machine'),
                ('services', 'service'),
                ('chargement', 'service'),
                ('emballage', 'service')
            ]
            
            for name, type_val in postes_data:
                cursor.execute(
                    "INSERT INTO postes (name, type) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=name",
                    (name, type_val)
                )
            
            # Get all operators with postes data
            cursor.execute("SELECT id, name, postes FROM operators WHERE postes IS NOT NULL AND postes != ''")
            operators = cursor.fetchall()
            
            print(f"Found {len(operators)} operators with postes data")
            
            # Get all available postes
            cursor.execute("SELECT id, name FROM postes")
            postes = {p['name']: p['id'] for p in cursor.fetchall()}
            
            migrated_count = 0
            
            for operator in operators:
                operator_id = operator['id']
                postes_string = operator['postes']
                
                # Parse the comma-separated postes string
                poste_names = [p.strip().lower() for p in postes_string.split(',') if p.strip()]
                
                # Find matching poste IDs
                poste_ids = []
                for poste_name in poste_names:
                    if poste_name in postes:
                        poste_ids.append(postes[poste_name])
                    else:
                        print(f"Warning: Poste '{poste_name}' not found in postes table for operator {operator['name']}")
                
                # Insert into operator_postes table
                if poste_ids:
                    # Remove any existing entries for this operator
                    cursor.execute("DELETE FROM operator_postes WHERE op_id = %s", (operator_id,))
                    
                    # Insert new entries
                    for poste_id in poste_ids:
                        cursor.execute(
                            "INSERT INTO operator_postes (op_id, poste_id) VALUES (%s, %s)",
                            (operator_id, poste_id)
                        )
                    
                    migrated_count += 1
                    print(f"Migrated operator {operator['name']} with postes: {poste_names}")
            
            connection.commit()
            print(f"Migration completed. {migrated_count} operators migrated.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    print("Starting operator postes migration...")
    migrate_operator_postes()
    print("Migration script completed.") 