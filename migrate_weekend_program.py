#!/usr/bin/env python3
"""Apply weekend program database migration."""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def migrate_weekend_program():
    migration_path = os.path.join(os.path.dirname(__file__), 'migration_weekend_program.sql')
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            for statement in sql_script.split(';'):
                stmt = statement.strip()
                if stmt and not stmt.startswith('--'):
                    cursor.execute(stmt)
        connection.commit()
        print('Weekend program migration completed successfully.')
    except Exception as e:
        connection.rollback()
        print(f'Weekend program migration failed: {e}')
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    migrate_weekend_program()
