#!/usr/bin/env python3
"""Verify SMTP configuration and optionally send a test email."""

import smtplib
import sys
from email.mime.text import MIMEText

import pymysql

from config import db_config, is_smtp_configured, smtp_config, verify_smtp_connection


def get_test_recipient():
    env_test = __import__('os').getenv('SMTP_TEST_TO', '').strip()
    if env_test:
        return env_test

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE role = 'admin' LIMIT 1")
            row = cursor.fetchone()
            return row['email'] if row else None
    finally:
        connection.close()


def send_test_email(recipient):
    message = MIMEText('SMTP test email from MPS schedule management.', 'plain', 'utf-8')
    message['Subject'] = 'MPS SMTP test'
    message['From'] = smtp_config['from_addr']
    message['To'] = recipient

    with smtplib.SMTP(smtp_config['host'], smtp_config['port'], timeout=15) as server:
        if smtp_config['use_tls']:
            server.starttls()
        if smtp_config['user'] and smtp_config['password']:
            server.login(smtp_config['user'], smtp_config['password'])
        code, _ = server.noop()
        if code != 250:
            raise smtplib.SMTPException(f'SMTP noop failed with code {code}')
        server.sendmail(smtp_config['from_addr'], [recipient], message.as_string())


def main():
    print('SMTP configuration (from .env via config.py):')
    print(f"  SMTP_HOST: {smtp_config['host'] or '(not set)'}")
    print(f"  SMTP_PORT: {smtp_config['port']}")
    print(f"  SMTP_USER: {smtp_config['user'] or '(not set)'}")
    print(f"  SMTP_FROM: {smtp_config['from_addr'] or '(not set)'}")
    print(f"  SMTP_PASSWORD: {'SET' if smtp_config['password'] else 'NOT SET'}")
    print(f"  SMTP_USE_TLS: {smtp_config['use_tls']}")

    if not is_smtp_configured():
        print('\nERROR: SMTP is not configured.')
        print('Copy .env.example to .env and set SMTP_HOST, SMTP_FROM, and credentials.')
        return 1

    try:
        verify_smtp_connection()
        print('\nSMTP connection test: OK')
    except Exception as exc:
        print(f'\nSMTP connection test: FAILED - {exc}')
        return 1

    recipient = get_test_recipient()
    if not recipient:
        print('\nConnection verified. No admin email found; skipping send test.')
        return 0

    try:
        send_test_email(recipient)
        print(f'Test email sent successfully to {recipient}')
    except Exception as exc:
        print(f'Test email send failed: {exc}')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
