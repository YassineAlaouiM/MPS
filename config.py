"""Application configuration loaded from the project .env file."""

import os
import smtplib

from dotenv import load_dotenv
from pymysql.cursors import DictCursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
}

smtp_config = {
    'host': (os.getenv('SMTP_HOST') or '').strip(),
    'port': int(os.getenv('SMTP_PORT', '587')),
    'user': (os.getenv('SMTP_USER') or '').strip(),
    'password': os.getenv('SMTP_PASSWORD') or '',
    'from_addr': (os.getenv('SMTP_FROM') or os.getenv('SMTP_USER') or '').strip(),
    'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
}


def is_smtp_configured():
    return bool(smtp_config['host'] and smtp_config['from_addr'])


def verify_smtp_connection():
    """Verify SMTP server reachability and credentials before sending."""
    if not is_smtp_configured():
        raise ValueError('SMTP is not configured (SMTP_HOST and SMTP_FROM are required)')

    with smtplib.SMTP(smtp_config['host'], smtp_config['port'], timeout=15) as server:
        if smtp_config['use_tls']:
            server.starttls()
        if smtp_config['user'] and smtp_config['password']:
            server.login(smtp_config['user'], smtp_config['password'])
        code, message = server.noop()
        if code != 250:
            raise smtplib.SMTPException(f'SMTP test failed: {code} {message.decode() if isinstance(message, bytes) else message}')
