from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
from waitress import serve
import socket
from functools import wraps
import json
from datetime import date
from pymysql.cursors import DictCursor
from typing import cast, List
from calendar import day_name
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root@localhost'),
    'database': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor  # <-- Use DictCursor directly
}

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, username, role FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
            if isinstance(user, dict):
                user = cast(dict, user)
                return User(user['id'], user['username'], user['role'])
    finally:
        connection.close()
    return None

def get_db_connection():
    connection = pymysql.connect(**db_config)
    return connection

@app.route('/')
def dashboard():
    ensure_today_history()
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return redirect(url_for('login'))

#Login and Registration
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT id, username, password, role FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                password_hash = user.get('password') if isinstance(user, dict) else None
                if isinstance(user, dict) and isinstance(password_hash, str) and check_password_hash(password_hash, password):
                    user = cast(dict, user)
                    user_obj = User(user['id'], user['username'], user['role'])
                    login_user(user_obj)
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid username or password')
        finally:
            connection.close()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if username exists
                sql = "SELECT id FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                if cursor.fetchone():
                    flash('Username already exists')
                    return redirect(url_for('register'))
                
                # Create new user
                sql = "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (username, generate_password_hash(password), email, 'admin'))
                connection.commit()
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
        finally:
            connection.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def get_machine_poste(machine_id: int, connection) -> dict:
    """Get the poste information for a machine"""
    with connection.cursor() as cursor:
        sql = '''
            SELECT p.id, p.name, p.type
            FROM machines m
            JOIN postes p ON m.poste_id = p.id
            WHERE m.id = %s
        '''
        cursor.execute(sql, (machine_id,))
        return cursor.fetchone()

@app.route('/machines')
@login_required
def machines():
    if not has_page_access('machines'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT m.*, p.name as poste_name, p.type as poste_type
                FROM machines m
                LEFT JOIN postes p ON m.poste_id = p.id
                ORDER BY m.status
            """
            cursor.execute(sql)
            machines = cursor.fetchall()
            sql = '''
                SELECT nfm.*, m.name 
                FROM non_functioning_machines nfm
                JOIN machines m ON nfm.machine_id = m.id
                ORDER BY (nfm.fixed_date),(nfm.reported_date) DESC
            '''
            cursor.execute(sql)
            non_functioning_machines = cursor.fetchall()
            # Fetch all postes for the dropdown
            cursor.execute("SELECT id, name FROM postes ORDER BY name")
            postes = cursor.fetchall()
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('machines', True) if current_user.role != 'admin' else True
    finally:
        connection.close()
    return render_template('machines.html', machines=machines, non_functioning_machines=non_functioning_machines, can_edit=can_edit, postes=postes)

def get_operator_postes(operator_id: int, connection) -> List[dict]:
    with connection.cursor() as cursor:
        sql = '''
            SELECT p.id, p.name, p.type
            FROM operator_postes op
            JOIN postes p ON op.poste_id = p.id
            WHERE op.op_id = %s
        '''
        cursor.execute(sql, (operator_id,))
        return cursor.fetchall()

def set_operator_postes(operator_id: int, poste_ids: List[int], connection):
    with connection.cursor() as cursor:
        # Remove existing
        cursor.execute("DELETE FROM operator_postes WHERE op_id = %s", (operator_id,))
        # Insert new
        for poste_id in poste_ids:
            cursor.execute("INSERT INTO operator_postes (op_id, poste_id) VALUES (%s, %s)", (operator_id, poste_id))

@app.route('/api/operators', methods=['POST'])
@login_required
def create_operator():
    data = request.get_json()
    name = data.get('name')
    arabic_name = data.get('arabic_name')
    postes = data.get('postes', '')  # old string for migration
    other_competences = data.get('other_competences', '')
    status = data.get('status', 'active')
    # New: poste_ids for new structure
    poste_ids = data.get('poste_ids', [])

    if not name or not arabic_name:
        return jsonify({'success': False, 'message': 'Name and Arabic name are required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert new operator without postes column for now
            sql = "INSERT INTO operators (name, arabic_name, other_competences, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, arabic_name, other_competences, status))
            operator_id = cursor.lastrowid
            # Insert into operator_postes if poste_ids provided
            if poste_ids:
                for poste_id in poste_ids:
                    cursor.execute("INSERT INTO operator_postes (op_id, poste_id) VALUES (%s, %s)", (operator_id, poste_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Operator created successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/operators/<int:operator_id>', methods=['GET'])
@login_required
def get_operator(operator_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, name, arabic_name, other_competences, status FROM operators WHERE id = %s"
            cursor.execute(sql, (operator_id,))
            operator = cursor.fetchone()
            if operator:
                # New: fetch postes from operator_postes
                operator['postes_list'] = get_operator_postes(operator_id, connection)
                return jsonify({'success': True, 'operator': operator})
            else:
                return jsonify({'success': False, 'message': 'Operator not found'})
    finally:
        connection.close()

@app.route('/api/operators/<int:operator_id>', methods=['PUT'])
@login_required
def update_operator(operator_id):
    data = request.get_json()
    name = data.get('name')
    arabic_name = data.get('arabic_name')
    postes = data.get('postes', '')  # old string for migration
    other_competences = data.get('other_competences', '')
    status = data.get('status')
    poste_ids = data.get('poste_ids', [])

    if not name or not arabic_name:
        return jsonify({'success': False, 'message': 'Name, and Arabic name are required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if operator exists
            sql = "SELECT id FROM operators WHERE id = %s"
            cursor.execute(sql, (operator_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Operator not found'})
            # Update operator details without postes column for now
            sql = "UPDATE operators SET name = %s, arabic_name = %s, other_competences = %s, status = %s WHERE id = %s"
            cursor.execute(sql, (name, arabic_name, other_competences, status, operator_id))
            # New: update operator_postes if poste_ids provided
            if poste_ids is not None:
                set_operator_postes(operator_id, poste_ids, connection)
            connection.commit()
            return jsonify({'success': True, 'message': 'Operator updated successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/operators')
@login_required
def operators():
    if not has_page_access('operators'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Temporarily remove postes column until migration is complete
            sql = "SELECT id, name, arabic_name, other_competences, status FROM operators ORDER BY (status='active') DESC, (status='absent') DESC, (status='inactive') DESC"
            cursor.execute(sql)
            operators = cursor.fetchall()
            # New: fetch postes for each operator
            for op in operators:
                op['postes_list'] = get_operator_postes(op['id'], connection)
            sql = '''
                SELECT a.*, o.name as operator_name
                FROM absences a
                JOIN operators o ON a.operator_id = o.id
                ORDER BY a.end_date DESC
            '''
            cursor.execute(sql)
            absences = cursor.fetchall()
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('operators', True) if current_user.role != 'admin' else True
    finally:
        connection.close()
    return render_template('operators.html', operators=operators, absences=absences, can_edit=can_edit)

@app.route('/production')
@login_required
def production():
    if not has_page_access('production'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM articles ORDER BY name"
            cursor.execute(sql)
            articles = cursor.fetchall()
            sql = "SELECT * FROM machines WHERE status = 'operational' ORDER BY name"
            cursor.execute(sql)
            machines = cursor.fetchall()
            sql = '''
                SELECT p.*, m.name as machine_name, m.type as machine_type, a.name as article_name
                FROM production p
                JOIN machines m ON p.machine_id = m.id
                LEFT JOIN articles a ON p.article_id = a.id
                ORDER BY p.status, p.start_date DESC
            '''
            cursor.execute(sql)
            production = cursor.fetchall()
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('production', True) if current_user.role != 'admin' else True
    finally:
        connection.close()
    return render_template('production.html', articles=articles, machines=machines, production=production, can_edit=can_edit)

def init_db():
    schema_file = "schema.sql"
    
    if not os.path.exists(schema_file):
        print(f"File '{schema_file}' not found.")
        return

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            with open(schema_file, "r", encoding="utf-8") as f:
                sql_commands = f.read()

            # Split and execute each statement
            for command in sql_commands.strip().split(";"):
                cmd = command.strip()
                if cmd:
                    try:
                        cursor.execute(cmd)
                    except Exception as e:
                        print(f"Error executing SQL:\n{cmd}\n→ {e}")
        connection.commit()
        print("Database initialized from schema.sql")
    finally:
        connection.close()
# Call init_db when the application starts
init_db()

#Machine Management
@app.route('/api/machines', methods=['POST'])
@login_required
def create_machine():
    data = request.get_json()
    name = data.get('name')
    status = data.get('status', 'operational')
    type = int(data.get('type', 0))  # Ensure it's an int (0 or 1)
    poste_id = data.get('poste_id')  # New: poste_id for machine type
    
    if not name:
        return jsonify({'success': False, 'message': 'Machine name is required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            print("Received poste_id:", poste_id)
            sql = "INSERT INTO machines (name, status, type, poste_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, status, type, poste_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Machine created successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/machines/<int:machine_id>', methods=['GET'])
@login_required
def get_machine(machine_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT m.*, p.name as poste_name, p.type as poste_type
                FROM machines m
                LEFT JOIN postes p ON m.poste_id = p.id
                WHERE m.id = %s
            """
            cursor.execute(sql, (machine_id,))
            machine = cursor.fetchone()
            if machine and isinstance(machine, dict):
                return jsonify({'success': True, 'machine': machine})
            else:
                return jsonify({'success': False, 'message': 'Machine not found'})
    finally:
        connection.close()

@app.route('/api/machines/<int:machine_id>', methods=['PUT'])
@login_required
def update_machine(machine_id):
    data = request.get_json()
    name = data.get('name')
    status = data.get('status')
    type = data.get('type')
    poste_id = data.get('poste_id')

    if not name or not status:
        return jsonify({'success': False, 'message': 'Name and status are required'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE machines SET name = %s, status = %s, type = %s, poste_id = %s WHERE id = %s"
            cursor.execute(sql, (name, status, type, poste_id, machine_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Machine updated successfully'})
    except Exception as e:
        print("Error updating machine:", e)  # Add this for debugging
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/machines/<int:machine_id>/toggle_type', methods=['POST'])
@login_required
def toggle_machine_type(machine_id):
    data = request.get_json()
    new_type = data.get('type', False)

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE machines SET type = %s WHERE id = %s"
            cursor.execute(sql, (new_type, machine_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Machine type updated successfully'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/machines/<int:machine_id>/poste', methods=['GET'])
@login_required

def get_machine_poste(machine_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT poste_id FROM machines WHERE id = %s"
            cursor.execute(sql, (machine_id,))
            poste_id = cursor.fetchone()
            return jsonify({'success': True, 'poste_id': poste_id})
    finally:
        connection.close()

@app.route('/api/machines/<int:machine_id>', methods=['DELETE'])
@login_required
def delete_machine(machine_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if machine is in non_functioning_machines
            sql = "SELECT id FROM non_functioning_machines WHERE machine_id = %s"
            cursor.execute(sql, (machine_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Cannot delete machine that is currently non-functioning'})
            
            # Check if machine is used in schedule
            sql = "SELECT id FROM schedule WHERE machine_id = %s"
            cursor.execute(sql, (machine_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Cannot delete machine that is used in schedule'})
            
            # Delete machine
            sql = "DELETE FROM machines WHERE id = %s"
            cursor.execute(sql, (machine_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Machine deleted successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()
#Completed Productions Management
def save_completed_production_to_history(production_id, completion_date):
    """Save completed production assignments to completed_productions table"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get all assignments for this production
            cursor.execute('''
                SELECT 
                    s.machine_id, m.name as machine_name,
                    s.production_id, p.article_id,
                    a.name as article_name, a.abbreviation as article_abbreviation,
                    s.operator_id, o.name as operator_name,
                    s.shift_id, sh.name as shift_name,
                    s.position, s.week_number, s.year
                FROM schedule s
                JOIN machines m ON s.machine_id = m.id
                JOIN production p ON s.production_id = p.id
                LEFT JOIN articles a ON p.article_id = a.id
                JOIN operators o ON s.operator_id = o.id
                JOIN shifts sh ON s.shift_id = sh.id
                WHERE s.production_id = %s
            ''', (production_id,))
            
            assignments = cursor.fetchall()
            
            # Insert each assignment into completed_productions
            for assignment in assignments:
                cursor.execute('''
                    INSERT INTO completed_productions (
                        production_id, machine_id, machine_name,
                        article_id, article_name, article_abbreviation,
                        operator_id, operator_name, shift_id, shift_name,
                        shift_start_time, shift_end_time, position, week_number, year, completion_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    assignment['production_id'], assignment['machine_id'], assignment['machine_name'],
                    assignment['article_id'], assignment['article_name'], assignment['article_abbreviation'],
                    assignment['operator_id'], assignment['operator_name'], assignment['shift_id'], assignment['shift_name'],
                    assignment['start_time'], assignment['end_time'], assignment['position'], assignment['week_number'], assignment['year'], completion_date
                ))
            
            connection.commit()
            return True
    except Exception as e:
        print(f"Error saving completed production to history: {str(e)}")
        connection.rollback()
        return False
    finally:
        connection.close()
#Non-Functioning Machines Management (Mahcines en panne)
def save_non_functioning_machine_to_history(machine_id, issue, reported_date, is_repair=False):
    """Save non-functioning machine event to history immediately"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get machine name
            cursor.execute("SELECT name FROM machines WHERE id = %s", (machine_id,))
            machine_result = cursor.fetchone()
            if not machine_result:
                return False
            
            machine_name = machine_result['name']
            # Handle different datetime formats
            try:
                reported_date_obj = datetime.strptime(reported_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    reported_date_obj = datetime.strptime(reported_date, '%Y-%m-%d %H:%M')
                except ValueError:
                    # If still fails, try just the date
                    reported_date_obj = datetime.strptime(reported_date, '%Y-%m-%d %H:%M')
            
            date_recorded = reported_date_obj.date()
            week = date_recorded.isocalendar()[1]
            year = date_recorded.year
            reported_time = reported_date_obj.strftime('%H:%M')
            
            connection.commit()
            return True
    except Exception as e:
        print(f"Error saving non-functioning machine to history: {str(e)}")
        connection.rollback()
        return False
    finally:
        connection.close()

@app.route('/api/non_functioning_machines', methods=['POST'])
@login_required
def create_non_functioning_machine():
    data = request.get_json()
    machine_id = data.get('machine_id')
    issue = data.get('issue')
    reported_date = data.get('reported_date') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    fixed_date = data.get('fixed_date')

    if not machine_id or not issue or not reported_date:
        return jsonify({'success': False, 'message': 'Machine ID, issue, and reported date are required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Update machine status to broken
            sql = "UPDATE machines SET status = 'broken' WHERE id = %s"
            cursor.execute(sql, (machine_id,))

            # Add to non_functioning_machines table
            sql = """
                INSERT INTO non_functioning_machines (machine_id, issue, reported_date)
                VALUES (%s, %s, %s)
            """
            # Get the machine name
            cursor.execute(sql, (machine_id, issue, reported_date))
            connection.commit()
            
            # Save to history immediately
            save_non_functioning_machine_to_history(machine_id, issue, reported_date, is_repair=False)
            
            return jsonify({'success': True, 'message': 'Non-functioning machine added successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

#Change machine status to operational by clicking on the "Marquer réparé" button
@app.route('/api/non_functioning_machines/<int:id>/fix', methods=['POST'])
@login_required
def mark_machine_fixed(id):
    data = request.get_json()
    fixed_date = data.get('fixed_date')

    if not fixed_date:
        return jsonify({'success': False, 'message': 'Fixed date is required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get machine_id and issue
            sql = "SELECT machine_id, issue FROM non_functioning_machines WHERE id = %s"
            cursor.execute(sql, (id,))
            result = cursor.fetchone()
            if not result or not isinstance(result, dict):
                return jsonify({'success': False, 'message': 'Record not found'})

            machine_id = result['machine_id']
            issue = result['issue']

            # Update non_functioning_machines with fixed date
            sql = "UPDATE non_functioning_machines SET fixed_date = %s WHERE id = %s"
            cursor.execute(sql, (fixed_date, id))

            # Update machine status to operational
            sql = "UPDATE machines SET status = 'operational' WHERE id = %s"
            cursor.execute(sql, (machine_id,))

            connection.commit()
            
            # Save repair event to history immediately
            save_non_functioning_machine_to_history(machine_id, issue, fixed_date, is_repair=True)
            
            return jsonify({'success': True, 'message': 'Machine marked as fixed successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

#Absences Management
@app.route('/api/absences/<int:id>', methods=['GET'])
@login_required
def get_absence(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT a.*, o.name as operator_name
                FROM absences a
                JOIN operators o ON a.operator_id = o.id
                WHERE a.id = %s
            """
            cursor.execute(sql, (id,))
            absence = cursor.fetchone()
            if not absence or not isinstance(absence, dict):
                return jsonify({'success': False, 'message': 'Absence not found'}), 404
            return jsonify(absence)
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/absences', methods=['POST'])
@login_required
def create_absence():
    data = request.get_json()
    operator_id = data.get('operator_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    reason = data.get('reason')
    
    if not all([operator_id, start_date, end_date, reason]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the dates are valid
            current_date = datetime.now().date()
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Add to absences table
            sql = """
                INSERT INTO absences (operator_id, start_date, end_date, reason)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (operator_id, start_date, end_date, reason))
            
            # Update operator status to 'absent' if the absence period includes current date
            if start_date_obj <= current_date <= end_date_obj:
                sql = "UPDATE operators SET status = 'absent' WHERE id = %s"
                cursor.execute(sql, (operator_id,))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Absence added successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/absences/<int:id>', methods=['PUT'])
@login_required
def update_absence(id):
    data = request.get_json()

    start_date = data.get('start_date')
    end_date = data.get('end_date')
    reason = data.get('reason')
    operator_id = data.get('operator_id')

    # ✅ Validate all fields are provided
    if not all([start_date, end_date, reason, operator_id]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get the current operator_id from the absence record
            sql = "SELECT operator_id FROM absences WHERE id = %s"
            cursor.execute(sql, (id,))
            current_absence = cursor.fetchone()
            
            if not current_absence or not isinstance(current_absence, dict):
                return jsonify({'success': False, 'message': 'Absence not found'}), 404
            
            old_operator_id = current_absence['operator_id']
            
            # Update the absence record
            sql = """
                UPDATE absences 
                SET start_date = %s, end_date = %s, reason = %s, operator_id = %s
                WHERE id = %s
            """
            cursor.execute(sql, (start_date, end_date, reason, operator_id, id))
            
            # Check if the dates include current date
            current_date = datetime.now().date()
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # If operator changed, reset old operator's status and update new operator's status
            if old_operator_id != operator_id:
                # Reset old operator's status to active if no current absences
                sql = """
                    UPDATE operators SET status = 'active'
                    WHERE id = %s AND NOT EXISTS (
                        SELECT 1 FROM absences 
                        WHERE operator_id = %s 
                        AND id != %s
                        AND CURDATE() BETWEEN start_date AND end_date
                    )
                """
                cursor.execute(sql, (old_operator_id, old_operator_id, id))
                
                # Update new operator's status if absence is current
                if start_date_obj <= current_date <= end_date_obj:
                    sql = "UPDATE operators SET status = 'absent' WHERE id = %s"
                    cursor.execute(sql, (operator_id,))
                else:
                    # Check if operator has other current absences
                    sql = """
                        UPDATE operators SET status = 'active'
                        WHERE id = %s AND NOT EXISTS (
                            SELECT 1 FROM absences 
                            WHERE operator_id = %s 
                            AND id != %s
                            AND CURDATE() BETWEEN start_date AND end_date
                        )
                    """
                    cursor.execute(sql, (operator_id, operator_id, id))
            else:
                # Update current operator's status based on dates
                if start_date_obj <= current_date <= end_date_obj:
                    sql = "UPDATE operators SET status = 'absent' WHERE id = %s"
                    cursor.execute(sql, (operator_id,))
                else:
                    # Check if operator has other current absences
                    sql = """
                        UPDATE operators SET status = 'active'
                        WHERE id = %s AND NOT EXISTS (
                            SELECT 1 FROM absences 
                            WHERE operator_id = %s 
                            AND id != %s
                            AND CURDATE() BETWEEN start_date AND end_date
                        )
                    """
                    cursor.execute(sql, (operator_id, operator_id, id))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Absence updated successfully'}), 200
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/absences/<int:id>', methods=['DELETE'])
@login_required
def delete_absence(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get operator_id before deleting
            sql = "SELECT operator_id FROM absences WHERE id = %s"
            cursor.execute(sql, (id,))
            result = cursor.fetchone()
            if not result or not isinstance(result, dict):
                return jsonify({'success': False, 'message': 'Record not found'})
            
            operator_id = result['operator_id']
            
            # Delete from absences
            sql = "DELETE FROM absences WHERE id = %s"
            cursor.execute(sql, (id,))
            
            # Update operator status to active
            sql = "UPDATE operators SET status = 'active' WHERE id = %s"
            cursor.execute(sql, (operator_id,))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Absence deleted successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

#Article Management
@app.route('/api/articles', methods=['POST'])
@login_required
def create_article():
    data = request.get_json()
    name = data.get('name')
    abbreviation = data.get('abbreviation')
    description = data.get('description')
    
    if not name:
        return jsonify({'success': False, 'message': 'Article name is required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO articles (name, abbreviation, description) VALUES (%s, %s, %s)"
            cursor.execute(sql, (name, abbreviation, description))
            connection.commit()
            return jsonify({'success': True, 'message': 'Article created successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/articles/<int:article_id>', methods=['GET'])
@login_required
def get_article(article_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM articles WHERE id = %s"
            cursor.execute(sql, (article_id,))
            article = cursor.fetchone()
            if article:
                return jsonify({'success': True, 'article': article})
            else:
                return jsonify({'success': False, 'message': 'Article not found'}), 404
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_article(article_id):
    data = request.get_json()
    name = data.get('name')
    abbreviation = data.get('abbreviation')
    description = data.get('description')

    if not name:
        return jsonify({'success': False, 'message': 'Article name is required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE articles SET name = %s, abbreviation = %s, description = %s WHERE id = %s"
            cursor.execute(sql, (name, abbreviation, description, article_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Article updated successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM articles WHERE id = %s"
            cursor.execute(sql, (article_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Article deleted successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

#Production Management
@app.route('/api/production', methods=['POST'])
@login_required
def create_production():
    data = request.get_json()
    machine_id = data.get('machine_id')
    article_id = data.get('article_id')
    if article_id in (None, ""):
        article_id = None
    quantity = data.get('quantity')
    if quantity in (None, ""):
        quantity = None
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not machine_id or not start_date:
        return jsonify({'success': False, 'message': 'Machine and start date are required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if machine is a service
            sql = "SELECT type FROM machines WHERE id = %s"
            cursor.execute(sql, (machine_id,))
            machine_result = cursor.fetchone()
            
            is_service = False
            if machine_result and isinstance(machine_result, dict) and machine_result.get('type'):
                is_service = True
            
            # For regular machines, article and quantity are required
            if not is_service and (not article_id or not quantity):
                return jsonify({'success': False, 'message': 'Article et quantité sont nécessaires pour les machines'})
            
            # Check if machine is already in production
            sql = """
                SELECT id, start_date, end_date, status 
                FROM production 
                WHERE machine_id = %s 
                AND status = 'active'
                AND (
                    (%s BETWEEN start_date AND COALESCE(end_date, %s))
                    OR (start_date BETWEEN %s AND COALESCE(%s, %s))
                )
            """
            cursor.execute(sql, (machine_id, start_date, start_date, start_date, end_date, start_date))
           
            
            # Add to production - for services, article_id and quantity are optional
            sql = """
                INSERT INTO production (machine_id, article_id, quantity, start_date, end_date, hour_start, hour_end, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            """
            cursor.execute(sql, (machine_id, article_id, quantity, start_date, end_date, None, None))
                
            connection.commit()
            return jsonify({'success': True, 'message': 'Production added successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/production/<int:id>', methods=['PUT'])
@login_required
def update_production(id):
    data = request.get_json()
    machine_id = data.get('machine_id')
    article_id = data.get('article_id')
    if article_id in (None, ""):
        article_id = None
    quantity = data.get('quantity')
    if quantity in (None, ""):
        quantity = None
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status = data.get('status')
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            updates = []
            params = []
            
            if machine_id:
                updates.append("machine_id = %s")
                params.append(machine_id)
            if article_id is not None:
                updates.append("article_id = %s")
                params.append(article_id)
            if quantity is not None:
                updates.append("quantity = %s")
                params.append(quantity)
            if start_date is not None:
                updates.append("start_date = %s")
                params.append(start_date)
            if end_date is not None:
                updates.append("end_date = %s")
                params.append(end_date)
            else:
                updates.append("end_date = NULL")
            if data.get('hour_start') is not None:
                updates.append("hour_start = %s")
                params.append(data.get('hour_start'))
            else:
                updates.append("hour_start = NULL")
            if data.get('hour_end') is not None:
                updates.append("hour_end = %s")
                params.append(data.get('hour_end'))
            else:
                updates.append("hour_end = NULL")
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            
            if not updates:
                return jsonify({'success': False, 'message': 'No fields to update'})
            
            params.append(id)
            sql = f"UPDATE production SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            connection.commit()
            return jsonify({'success': True, 'message': 'Production updated successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/production/<int:id>', methods=['GET'])
@login_required
def get_production(id):
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
                SELECT p.*, m.name as machine_name, m.type as machine_type, a.name as article_name
                FROM production p
                JOIN machines m ON p.machine_id = m.id
                LEFT JOIN articles a ON p.article_id = a.id
                WHERE p.id = %s
            """
            cursor.execute(sql, (id,))
            production = cursor.fetchone()
            
            if production:
                # Handle NULL values for hour fields and convert timedelta to string
                hour_start = None
                hour_end = None
                
                if production['hour_start'] is not None:
                    if hasattr(production['hour_start'], 'total_seconds'):
                        # Convert timedelta to HH:MM:SS format
                        total_seconds = int(production['hour_start'].total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        hour_start = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        hour_start = str(production['hour_start'])
                
                if production['hour_end'] is not None:
                    if hasattr(production['hour_end'], 'total_seconds'):
                        # Convert timedelta to HH:MM:SS format
                        total_seconds = int(production['hour_end'].total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        hour_end = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        hour_end = str(production['hour_end'])
                
                return jsonify({
                    'id': production['id'],
                    'machine_id': production['machine_id'],
                    'machine_name': production['machine_name'],
                    'machine_type': production['machine_type'],
                    'article_id': production['article_id'],
                    'article_name': production['article_name'],
                    'quantity': production['quantity'],
                    'start_date': production['start_date'],
                    'end_date': production['end_date'],
                    'hour_start': hour_start,
                    'hour_end': hour_end,
                    'status': production['status']
                })
            else:
                return jsonify({'success': False, 'message': 'Production record not found'}), 404
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/production/<int:id>', methods=['DELETE'])
@login_required
def delete_production(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM production WHERE id = %s"
            cursor.execute(sql, (id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Production record deleted successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/schedule', methods=['POST'])
@login_required
def create_schedule():
    data = request.get_json()
    machine_id = data.get('machine_id')
    operator_id = data.get('operator_id')
    shift_id = data.get('shift_id')
    week_number = data.get('week_number')
    year = data.get('year')
    
    if not all([machine_id, operator_id, shift_id, week_number, year]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if operator is already assigned for this week
                cursor.execute("""
                    SELECT id FROM schedule 
                    WHERE operator_id = %s AND week_number = %s AND year = %s
                """, (operator_id, week_number, year))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Operator already assigned for this week'})
                
                # Create new assignment
                cursor.execute("""
                    INSERT INTO schedule (machine_id, operator_id, shift_id, week_number, year)
                    VALUES (%s, %s, %s, %s, %s)
                """, (machine_id, operator_id, shift_id, week_number, year))
                conn.commit()
                return jsonify({'success': True, 'message': 'Assignment created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/schedule/<int:assignment_id>', methods=['DELETE'])
@login_required
def delete_schedule(assignment_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get the assignment details before deleting
                cursor.execute("""
                    SELECT s.*, m.name as machine_name, o.name as operator_name, sh.name as shift_name,
                           sh.start_time, sh.end_time, p.article_id, a.name as article_name, a.abbreviation as article_abbreviation
                    FROM schedule s
                    JOIN machines m ON s.machine_id = m.id
                    JOIN operators o ON s.operator_id = o.id
                    JOIN shifts sh ON s.shift_id = sh.id
                    LEFT JOIN production p ON s.production_id = p.id
                    LEFT JOIN articles a ON p.article_id = a.id
                    WHERE s.id = %s
                """, (assignment_id,))
                
                assignment = cursor.fetchone()
                if assignment:
                    # Save the assignment to history before deleting
                    today = datetime.now().date()
                    week = today.isocalendar()[1]
                    year = today.year
                    
                    cursor.execute('''
                        INSERT INTO daily_schedule_history (
                            date_recorded, week_number, year,
                            machine_id, production_id, operator_id, shift_id, position,
                            machine_name, operator_name, shift_name, shift_start_time, shift_end_time,
                            article_name, article_abbreviation
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        today, week, year,
                        assignment['machine_id'], assignment.get('production_id'), assignment['operator_id'],
                        assignment['shift_id'], assignment['position'],
                        assignment['machine_name'], assignment['operator_name'], assignment['shift_name'],
                        assignment['start_time'], assignment['end_time'],
                        assignment['article_name'] or '', assignment['article_abbreviation'] or ''
                    ))
                
                # Now delete the assignment
                cursor.execute("DELETE FROM schedule WHERE id = %s", (assignment_id,))
                conn.commit()
                return jsonify({'success': True, 'message': 'Assignment deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/schedule/<int:assignment_id>', methods=['PUT'])
@login_required
def update_schedule(assignment_id):
    data = request.get_json()
    machine_id = data.get('machine_id')
    operator_id = data.get('operator_id')
    shift_id = data.get('shift_id')
    
    if not all([machine_id, operator_id, shift_id]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get current week and year for the assignment
                cursor.execute("""
                    SELECT week_number, year FROM schedule WHERE id = %s
                """, (assignment_id,))
                result = cursor.fetchone()
                if not result:
                    return jsonify({'success': False, 'message': 'Assignment not found'})
                
                # Check if operator is already assigned for this week
                cursor.execute("""
                    SELECT id FROM schedule 
                    WHERE operator_id = %s 
                    AND week_number = %s 
                    AND year = %s 
                    AND id != %s
                """, (operator_id, result['week_number'], result['year'], assignment_id))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Operator already assigned for this week'})
                
                # Update assignment
                cursor.execute("""
                    UPDATE schedule 
                    SET machine_id = %s, operator_id = %s, shift_id = %s
                    WHERE id = %s
                """, (machine_id, operator_id, shift_id, assignment_id))
                conn.commit()
                return jsonify({'success': True, 'message': 'Assignment updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def get_machines_in_production():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT m.*, p.article_id, a.name as article_name
                    FROM machines m
                    JOIN production p ON m.id = p.machine_id
                    LEFT JOIN articles a ON p.article_id = a.id
                    WHERE p.status = 'active'
                    AND CURDATE() BETWEEN p.start_date AND COALESCE(p.end_date, CURDATE())
                """)
                return cursor.fetchall()
    except Exception as e:
        flash(f"Error loading machines in production: {str(e)}", "error")
        return []

#Get Operators with their absence status for the selected week
def get_operators(week=None, year=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # If week and year are not provided, use current date
                if week is None or year is None:
                    current_date = datetime.now()
                    week = current_date.isocalendar()[1]
                    year = current_date.year
                
                # Calculate week start and end dates
                cursor.execute("""
                    SELECT 
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Monday'), '%%Y %%u %%W') as week_start,
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Sunday'), '%%Y %%u %%W') as week_end
                """, (year, week, year, week))
                week_dates = cursor.fetchone()
                
                # Get operators with their absence status for the selected week
                cursor.execute("""
                    SELECT 
                        o.*,
                        MAX(a.start_date) as start_date,
                        MAX(a.end_date) as end_date,
                        CASE 
                            WHEN MAX(a.start_date) IS NOT NULL AND MAX(a.end_date) IS NOT NULL THEN
                                CASE 
                                    WHEN DATEDIFF(MAX(a.end_date), MAX(a.start_date)) > 7
                                        AND %s BETWEEN MAX(a.start_date) AND MAX(a.end_date)    
                                    THEN 'long_absence'
                                    WHEN %s BETWEEN MAX(a.start_date) AND MAX(a.end_date)
                                    THEN 'current_absence'
                                    WHEN MAX(a.start_date) BETWEEN %s AND %s
                                    THEN 'upcoming_absence'
                                    ELSE 'no_absence'
                                END
                            ELSE 'no_absence'
                        END as absence_status
                    FROM operators o
                    LEFT JOIN absences a ON o.id = a.operator_id 
                        AND (
                            %s BETWEEN a.start_date AND a.end_date
                            OR a.start_date BETWEEN %s AND %s
                        )
                    WHERE o.status IN ('active', 'absent')
                    GROUP BY o.id, o.name, o.arabic_name, o.status, o.last_shift_id
                """, (week_dates['week_start'], week_dates['week_start'],
                      week_dates['week_start'], week_dates['week_end'],
                      week_dates['week_start'],
                      week_dates['week_start'], week_dates['week_end']))
                return cursor.fetchall()
    except Exception as e:
        flash(f"Error loading operators: {str(e)}", "error")
        return []

def get_shifts():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM shifts")
                shifts = cursor.fetchall()
                return shifts
    except Exception as e:
        print(f"Error in get_shifts: {str(e)}")  #Debug print
        flash(f"Error loading shifts: {str(e)}", "error")
        return []

#Shift Management
@app.route('/shifts')
@login_required
def shifts():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM shifts")
                shifts = cursor.fetchall()
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('shifts', True) if current_user.role != 'admin' else True
    except Exception as e:
        flash(f"Error loading shifts: {str(e)}", "error")
        shifts = []
        can_edit = False
    return render_template('shifts.html', shifts=shifts, can_edit=can_edit)

@app.route('/api/shifts', methods=['POST'])
@login_required
def create_shift():
    data = request.get_json()
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([name, start_time, end_time]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO shifts (name, start_time, end_time)
                    VALUES (%s, %s, %s)
                """, (name, start_time, end_time))
                conn.commit()
                return jsonify({'success': True, 'message': 'Shift created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/shifts/<int:shift_id>', methods=['PUT'])
@login_required
def update_shift(shift_id):
    data = request.get_json()
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([name, start_time, end_time]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE shifts 
                    SET name = %s, start_time = %s, end_time = %s
                    WHERE id = %s
                """, (name, start_time, end_time, shift_id))
                conn.commit()
                return jsonify({'success': True, 'message': 'Shift updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/shifts/<int:shift_id>', methods=['DELETE'])
@login_required
def delete_shift(shift_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if shift is used in any schedule
                cursor.execute("""
                    SELECT id FROM schedule WHERE shift_id = %s
                """, (shift_id,))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Cannot delete shift that is used in schedule'})
                
                cursor.execute("DELETE FROM shifts WHERE id = %s", (shift_id,))
                conn.commit()
                return jsonify({'success': True, 'message': 'Shift deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/check_shifts')
def check_shifts():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM shifts")
                shifts = cursor.fetchall()
                return jsonify({'success': True, 'shifts': shifts})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#Schedule Management
@app.route('/schedule')
@login_required
def schedule():
    ensure_today_history()
    if not has_page_access('schedule'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    week = request.args.get('week', default=datetime.now().isocalendar()[1], type=int)
    year = request.args.get('year', default=datetime.now().year, type=int)
    machines = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Monday'), '%%Y %%u %%W') as week_start,
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Sunday'), '%%Y %%u %%W') as week_end
                """, (year, week, year, week))
                week_dates = cursor.fetchone()
                if not week_dates or not week_dates['week_start'] or not week_dates['week_end']:
                    flash(f"Error calculating week dates for week {week} of {year}", "error")
                    return render_template('schedule.html', machines=[], operators=[], shifts=[], assignments=[], can_edit=False)
                cursor.execute("""
                    SELECT m.*, p.id as production_id, p.article_id, a.name as article_name,
                           CASE WHEN nfm.id IS NOT NULL THEN 1 ELSE 0 END as is_nfm
                    FROM machines m
                    JOIN production p ON m.id = p.machine_id
                    LEFT JOIN articles a ON p.article_id = a.id
                    LEFT JOIN non_functioning_machines nfm ON m.id = nfm.machine_id 
                        AND (nfm.fixed_date IS NULL OR DATE(nfm.fixed_date) > CURDATE())
                    WHERE p.status = 'active'
                    AND (
                        (p.start_date <= %s AND (p.end_date IS NULL OR p.end_date >= %s))
                        OR (p.start_date BETWEEN %s AND %s)
                        OR ((p.end_date IS NOT NULL) AND p.end_date BETWEEN %s AND %s)
                    )
                    ORDER BY m.type, m.name, p.start_date
                """, (week_dates['week_end'], week_dates['week_start'],
                      week_dates['week_start'], week_dates['week_end'],
                      week_dates['week_start'], week_dates['week_end']))
                machines = cursor.fetchall()
                # --- Add for modal ---
                cursor.execute("SELECT * FROM articles ORDER BY name")
                articles = cursor.fetchall()
                cursor.execute("SELECT * FROM machines WHERE status = 'operational' ORDER BY name")
                all_machines = cursor.fetchall()
                # --- End add ---
                # Get operators for dropdown (exclude inactive)
                operators = get_operators(week, year)
                
                # Get all operators including inactive for display purposes
                cursor.execute("""
                    SELECT o.*, 
                           MAX(a.start_date) as start_date,
                           MAX(a.end_date) as end_date,
                           CASE 
                               WHEN MAX(a.start_date) IS NOT NULL AND MAX(a.end_date) IS NOT NULL THEN
                                   CASE 
                                       WHEN DATEDIFF(MAX(a.end_date), MAX(a.start_date)) > 7
                                           AND %s BETWEEN MAX(a.start_date) AND MAX(a.end_date)    
                                       THEN 'long_absence'
                                       WHEN %s BETWEEN MAX(a.start_date) AND MAX(a.end_date)
                                       THEN 'current_absence'
                                       WHEN MAX(a.start_date) BETWEEN %s AND %s
                                       THEN 'upcoming_absence'
                                       ELSE 'no_absence'
                                   END
                               ELSE 'no_absence'
                           END as absence_status
                    FROM operators o
                    LEFT JOIN absences a ON o.id = a.operator_id 
                        AND (
                            %s BETWEEN a.start_date AND a.end_date
                            OR a.start_date BETWEEN %s AND %s
                        )
                    GROUP BY o.id, o.name, o.arabic_name, o.status, o.last_shift_id
                """, (week_dates['week_start'], week_dates['week_start'],
                      week_dates['week_start'], week_dates['week_end'],
                      week_dates['week_start'],
                      week_dates['week_start'], week_dates['week_end']))
                all_operators = cursor.fetchall()
                shifts = get_shifts()
                cursor.execute("""
                    SELECT s.id, s.machine_id, s.production_id, s.operator_id, s.shift_id, s.position,
                           s.week_number, s.year,
                           m.name as machine_name, o.name as operator_name, sh.name as shift_name,
                           p.article_id, a.name as article_name
                    FROM schedule s
                    JOIN machines m ON s.machine_id = m.id
                    JOIN production p ON s.production_id = p.id
                    LEFT JOIN articles a ON p.article_id = a.id
                    JOIN operators o ON s.operator_id = o.id
                    JOIN shifts sh ON s.shift_id = sh.id
                    WHERE s.week_number = %s AND s.year = %s
                    ORDER BY m.name, p.start_date, sh.id, s.position
                """, (week, year))
                assignments = cursor.fetchall()
            current_access = get_user_accessible_pages(current_user.id)
            can_edit = current_access.get('schedule', True) if current_user.role != 'admin' else True
    except Exception as e:
        flash(f"Error loading machines: {str(e)}", "error")
        return render_template('schedule.html', machines=[], operators=[], shifts=[], assignments=[], can_edit=False)
    return render_template('schedule.html', 
                         week=week,
                         year=year,
                         machines=machines,
                         all_machines=all_machines,
                         operators=operators,
                         all_operators=all_operators,
                         shifts=shifts,
                         assignments=assignments,
                         can_edit=can_edit,
                         articles=articles)
#Get Schedule Assignments
@app.route('/api/schedule', methods=['GET'])
@login_required
def get_schedule():
    week = request.args.get('week', type=int)
    year = request.args.get('year', type=int)
    
    if not week or not year:
        return jsonify({'success': False, 'message': 'Week and year are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT s.id, m.name as machine_name, o.name as operator_name, sh.name as shift_name
                    FROM schedule s
                    JOIN machines m ON s.machine_id = m.id
                    JOIN operators o ON s.operator_id = o.id
                    JOIN shifts sh ON s.shift_id = sh.id
                    WHERE s.week_number = %s AND s.year = %s
                """, (week, year))
                assignments = cursor.fetchall()
                return jsonify({'success': True, 'assignments': assignments})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#Schedule Assignment
@app.route('/assign_operator', methods=['POST'])
@login_required
def assign_operator():
    machine_id = request.form['machine_id']
    operator_id = request.form['operator_id']
    shift_id = request.form['shift_id']
    week_number = request.form['week_number']
    year = request.form['year']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if operator is already assigned
            sql = """
                SELECT id FROM schedule 
                WHERE operator_id = %s AND week_number = %s AND year = %s
            """
            cursor.execute(sql, (operator_id, week_number, year))
            if cursor.fetchone():
                flash('Operator already assigned for this week')
                return redirect(url_for('schedule', week=week_number, year=year))
            
            # Assign operator
            sql = """
                INSERT INTO schedule (machine_id, operator_id, shift_id, week_number, year)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (machine_id, operator_id, shift_id, week_number, year))
            connection.commit()
    finally:
        connection.close()
    
    return redirect(url_for('schedule', week=week_number, year=year))

#Schedule Confirmation
@app.route('/api/schedule/confirm', methods=['POST'])
@login_required
def confirm_assignments():
    data = request.json
    assignments = data['assignments']
    week_number = data['week_number']
    year = data['year']

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Before deleting, insert only completed productions into completed_productions
            cursor.execute("""
                SELECT 
                    s.id as schedule_id,
                    s.machine_id, m.name as machine_name,
                    s.production_id, p.article_id,
                    a.name as article_name, a.abbreviation as article_abbreviation,
                    s.operator_id, o.name as operator_name,
                    s.shift_id, sh.name as shift_name,
                    sh.start_time, sh.end_time,
                    s.position, s.week_number, s.year
                FROM schedule s
                JOIN machines m ON s.machine_id = m.id
                JOIN production p ON s.production_id = p.id
                LEFT JOIN articles a ON p.article_id = a.id
                JOIN operators o ON s.operator_id = o.id
                JOIN shifts sh ON s.shift_id = sh.id
                WHERE s.week_number = %s AND s.year = %s
                AND p.status = 'completed'
                AND p.end_date IS NOT NULL
            """, (week_number, year))
            old_assignments = cursor.fetchall()
            
            # Get completion dates for each production
            for assignment in old_assignments:
                cursor.execute("""
                    SELECT end_date FROM production WHERE id = %s
                """, (assignment['production_id'],))
                production_result = cursor.fetchone()
                
                if production_result and production_result['end_date']:
                    completion_date = production_result['end_date']
                    
                    cursor.execute('''
                        INSERT INTO completed_productions (
                            production_id, machine_id, machine_name,
                            article_id, article_name, article_abbreviation,
                            operator_id, operator_name, shift_id, shift_name,
                            shift_start_time, shift_end_time, position, week_number, year, completion_date
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        assignment['production_id'], assignment['machine_id'], assignment['machine_name'],
                        assignment['article_id'], assignment['article_name'], assignment['article_abbreviation'],
                        assignment['operator_id'], assignment['operator_name'], assignment['shift_id'], assignment['shift_name'],
                        assignment['start_time'], assignment['end_time'], assignment['position'], assignment['week_number'], assignment['year'], completion_date
                    ))

            # 2. Clear existing assignments for this week
            cursor.execute("""
                DELETE FROM schedule 
                WHERE week_number = %s AND year = %s
            """, (week_number, year))
            
            # 3. Save new assignments to the database
            for assignment in assignments:
                cursor.execute("""
                    INSERT INTO schedule (machine_id, production_id, operator_id, shift_id, position, week_number, year)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (assignment['machine_id'], assignment['production_id'], assignment['operator_id'], 
                      assignment['shift_id'], assignment['position'], week_number, year))
            # --- Fix: Update last_shift_id for all assigned operators ---
            for assignment in assignments:
                if assignment['operator_id'] is not None:
                    cursor.execute(
                        "UPDATE operators SET last_shift_id = %s WHERE id = %s",
                        (assignment['shift_id'], assignment['operator_id'])
                    )
            connection.commit()
            save_daily_schedule_history()  # Automatically save after confirmation
            return jsonify({'success': True, 'message': 'Assignments confirmed successfully.'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

#Random Assignments with Rotation Management
@app.route('/api/schedule/random', methods=['POST'])
@login_required
def random_assignments():
    data = request.json
    week = data.get('week_number')
    year = data.get('year')
    machine_ids = data.get('machine_ids', [])
    
    if not week or not year:
        return jsonify({'success': False, 'message': 'Week and year are required'})
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Calculate week dates
                cursor.execute("""
                    SELECT 
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Monday'), '%%Y %%u %%W') as week_start,
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Sunday'), '%%Y %%u %%W') as week_end
                """, (year, week, year, week))
                week_dates = cursor.fetchone()
                
                if not week_dates or not week_dates['week_start'] or not week_dates['week_end']:
                    return jsonify({'success': False, 'message': f'Error calculating week dates for week {week} of {year}'})
                
                # Get all available operators (excluding absent ones)
                cursor.execute("""
                    SELECT o.id, o.name, o.last_shift_id
                    FROM operators o
                    LEFT JOIN absences a ON o.id = a.operator_id 
                        AND CURDATE() BETWEEN a.start_date AND a.end_date
                    WHERE o.status = 'active' AND a.id IS NULL
                """)
                operators = cursor.fetchall()
                
                if not operators:
                    return jsonify({'success': False, 'message': 'No active operators available'})
                
                # Get selected machines and their production records
                if machine_ids:
                    cursor.execute("""
                        SELECT m.id, m.name, m.poste_id, p.id as production_id, p.article_id, a.name as article_name
                        FROM machines m
                        JOIN production p ON m.id = p.machine_id
                        LEFT JOIN articles a ON p.article_id = a.id
                        WHERE m.id IN %s AND m.status = 'operational'
                        AND p.status = 'active'
                        AND (
                            (p.start_date <= %s AND (p.end_date IS NULL OR p.end_date >= %s))
                            OR (p.start_date BETWEEN %s AND %s)
                            OR ((p.end_date IS NOT NULL) AND p.end_date BETWEEN %s AND %s)
                        )
                    """, (tuple(machine_ids), week_dates['week_end'], week_dates['week_start'],
                          week_dates['week_start'], week_dates['week_end'],
                          week_dates['week_start'], week_dates['week_end']))
                else:
                    cursor.execute("""
                        SELECT m.id, m.name, m.poste_id, p.id as production_id, p.article_id, a.name as article_name
                        FROM machines m
                        JOIN production p ON m.id = p.machine_id
                        LEFT JOIN articles a ON p.article_id = a.id
                        WHERE m.status = 'operational'
                        AND p.status = 'active'
                        AND (
                            (p.start_date <= %s AND (p.end_date IS NULL OR p.end_date >= %s))
                            OR (p.start_date BETWEEN %s AND %s)
                            OR ((p.end_date IS NOT NULL) AND p.end_date BETWEEN %s AND %s)
                        )
                    """, (week_dates['week_end'], week_dates['week_start'],
                          week_dates['week_start'], week_dates['week_end'],
                          week_dates['week_start'], week_dates['week_end']))
                machines = cursor.fetchall()
                
                if not machines:
                    return jsonify({'success': False, 'message': 'No machines available'})
                
                # Get shifts for the first three shifts (1, 2, 3) (Model 1)
                cursor.execute("SELECT id, name FROM shifts WHERE id IN (1, 2, 3) ORDER BY id")
                shifts = cursor.fetchall()
                
                if not shifts:
                    return jsonify({'success': False, 'message': 'No shifts available'})
                
                # Shuffle machines to randomize assignments
                random.shuffle(machines)

                assignments = []
                available_operators = operators.copy()

                # Fetch all operator-poste relationships
                cursor.execute("SELECT op_id, poste_id FROM operator_postes")
                operator_postes = cursor.fetchall()
                # Build a mapping: operator_id -> set of poste_ids
                operator_poste_map = {}
                for op in operator_postes:
                    operator_poste_map.setdefault(op['op_id'], set()).add(op['poste_id'])

                # For each machine, filter eligible operators
                for machine in machines:
                    eligible_operators = [
                        op for op in available_operators
                        if machine['poste_id'] in operator_poste_map.get(op['id'], set())
                    ]
                    if not eligible_operators:
                        # No eligible operator for this machine/shift
                        for shift in shifts:
                            assignments.append({
                                'machine_id': machine['id'],
                                'production_id': machine['production_id'],
                                'operator_id': None,
                                'shift_id': shift['id'],
                                'machine_name': machine['name'],
                                'operator_name': None,
                                'shift_name': shift['name']
                            })
                        continue

                    for shift in shifts:
                        if not eligible_operators:
                            assignments.append({
                                'machine_id': machine['id'],
                                'production_id': machine['production_id'],
                                'operator_id': None,
                                'shift_id': shift['id'],
                                'machine_name': machine['name'],
                                'operator_name': None,
                                'shift_name': shift['name']
                            })
                            continue

                        # Rotation logic, but only among eligible_operators
                        selected_operator = None
                        for operator in eligible_operators:
                            last_shift_id = operator['last_shift_id']
                            if last_shift_id is None:
                                if shift['id'] == 1:
                                    selected_operator = operator
                                    break
                            else:
                                if last_shift_id == 1:
                                    next_shift = 3
                                elif last_shift_id == 3:
                                    next_shift = 2
                                else:
                                    next_shift = 1

                            if shift['id'] == next_shift:
                                selected_operator = operator
                                break

                        if not selected_operator:
                            selected_operator = eligible_operators[0]

                        available_operators.remove(selected_operator)
                        eligible_operators.remove(selected_operator)

                        assignments.append({
                            'machine_id': machine['id'],
                            'production_id': machine['production_id'],
                            'operator_id': selected_operator['id'],
                            'shift_id': shift['id'],
                            'machine_name': machine['name'],
                            'operator_name': selected_operator['name'],
                            'shift_name': shift['name']
                        })

                        # Update operator's last shift in database (Rotation)
                        cursor.execute("""
                            UPDATE operators 
                            SET last_shift_id = %s 
                            WHERE id = %s
                        """, (shift['id'], selected_operator['id']))
                
                conn.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Random assignments with rotation generated successfully',
                    'assignments': assignments
                })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#PDF - Schedule Export
@app.route('/export_schedule', methods=['GET'])
@login_required
def export_sch():
    week = request.args.get('week', type=int)
    year = request.args.get('year', type=int)
    name_type = request.args.get('name_type', 'latin')  # Default to latin names
    
    if not week or not year:
        return jsonify({"error": "Week and year parameters are required"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Select arabic or french name
        name_field = 'o.arabic_name' if name_type == 'arabic' else 'o.name'
        
        cursor.execute(f'''
            SELECT 
                m.name AS machine_name,
                m.type AS machine_type,
                p.id as production_id,
                a.name as article_name,
                a.abbreviation as article_abbreviation,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 1 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_1,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 2 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_2,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 3 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_3,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 4 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_4,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 5 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_5,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 6 THEN {name_field}
                        ELSE NULL
                    END
                    ORDER BY sc.position
                ) AS shift_6
            FROM machines m
            INNER JOIN schedule sc ON m.id = sc.machine_id AND sc.week_number = %s AND sc.year = %s
            INNER JOIN production p ON sc.production_id = p.id
            LEFT JOIN articles a ON p.article_id = a.id
            LEFT JOIN shifts s ON sc.shift_id = s.id
            LEFT JOIN operators o ON sc.operator_id = o.id
            WHERE m.status != 'broken'
            GROUP BY m.id, m.name, p.id, a.name, a.abbreviation
            HAVING shift_1 IS NOT NULL 
                OR shift_2 IS NOT NULL 
                OR shift_3 IS NOT NULL 
                OR shift_4 IS NOT NULL 
                OR shift_5 IS NOT NULL 
                OR shift_6 IS NOT NULL
            ORDER BY m.type, m.name, p.start_date
        ''', (week, year))
        schedule_data = cursor.fetchall()
        conn.close()
        
        # Create a BytesIO buffer for the PDF
        buffer = BytesIO()
        
        # Create the PDF object, using BytesIO as its "file"
        page_width, page_height = portrait(A4)
        p = canvas.Canvas(buffer, pagesize=portrait(A4))
        
        # Register fonts for normal and bold
        try:
            if name_type == 'arabic' or (lang if 'lang' in locals() else None) == 'ar':
                font_name = 'Amiri'
                bold_font_name = 'Amiri'
            else:
                font_name = 'Amiri'
                bold_font_name = 'Amiri'
            font_paths = [
                '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
                '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
                'static/fonts/Amiri-Regular.ttf'
            ]
            bold_font_paths = [
                'static/fonts/Amiri-Bold.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
            font_found = False
            for path in font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arabic', path))
                    font_name = 'Arabic'
                    font_found = True
                    break
            if not font_found:
                pdfmetrics.registerFont(TTFont('Arabic', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                font_name = 'Arabic'
            bold_font_found = False
            for path in bold_font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arabic-Bold', path))
                    bold_font_name = 'Arabic-Bold'
                    bold_font_found = True
                    break
            if not bold_font_found:
                bold_font_name = font_name
        except Exception as e:
            print(f"Font registration error: {str(e)}")
            font_name = 'Helvetica'
            bold_font_name = 'Helvetica-Bold'

        def add_page_header(canvas, page_num, total_pages):
            # Add title and week dates as a single string, centered
            canvas.setFont('Helvetica-Bold', 20)  # Use Helvetica for page header
            canvas.setFillColor(header_color)
            title_text = "Programme"
            
            # Calculate week dates
            def get_week_dates(year, week):
                jan_fourth = datetime(year, 1, 4)
                monday_week1 = jan_fourth - timedelta(days=jan_fourth.isocalendar()[2] - 1)
                target_monday = monday_week1 + timedelta(weeks=week-1)
                target_sunday = target_monday + timedelta(days=6)
                return target_monday, target_sunday

            week_start, week_end = get_week_dates(year, week)
            week_dates = f"Du {week_start.strftime('%d/%m/%Y')} à {week_end.strftime('%d/%m/%Y')}"

            y = page_height - 40
            header_text = f"{title_text} {week_dates}"
            # Center the header text
            canvas.drawCentredString(page_width / 2, y, header_text)

        def process_text(text, is_header=False, is_machine=False):
            if not text:
                return ""
            text = str(text)
            
            if is_header:
                return text
            
            if name_type == 'arabic' and any(ord(char) in range(0x0600, 0x06FF) for char in text):
                if not is_machine:
                    operators = text.split(',')
                    if len(operators) > 1:
                        # Multiple operators case
                        processed_operators = []
                        for operator in operators:
                            operator = operator.strip()
                            # If operator name is longer than 20, break last word(s) into new line
                            if len(operator) > 20:
                                words = operator.split()
                                if len(words) > 1:
                                    # Move last word to new line
                                    processed_operators.append(' '.join(words[:-1]) + '\n' + words[-1])
                                else:
                                    processed_operators.append(operator)
                            else:
                                processed_operators.append(operator)
                        text = '\n+ '.join(processed_operators)
                    else:
                        # Single operator case
                        operator = text.strip()
                        if len(operator) > 20:
                            words = operator.split()
                            if len(words) > 1:
                                text = ' '.join(words[:-1]) + '\n' + words[-1]
                            else:
                                text = operator
                        else:
                            text = operator
                reshaped_text = arabic_reshaper.reshape(text)
                return get_display(reshaped_text)
            elif is_machine:
                return text.upper()
            elif not is_header:
                operators = text.split(',')
                if len(operators) > 1:
                    # Multiple operators case
                    processed_operators = []
                    for operator in operators:
                        operator = operator.strip()
                        operator_cap = operator.capitalize()
                        # If operator name is longer than 20, break last word(s) into new line
                        if len(operator_cap) > 20:
                            words = operator_cap.split()
                            if len(words) > 1:
                                processed_operators.append(' '.join(words[:-1]) + '\n' + words[-1].capitalize())
                            else:
                                processed_operators.append(operator_cap)
                        else:
                            processed_operators.append(operator_cap)
                    return '\n+ '.join(processed_operators)
                else:
                    # Single operator case
                    operator = text.strip().capitalize()
                    if len(operator) > 20:
                        words = operator.split()
                        if len(words) > 1:
                            return ' '.join(words[:-1]) + '\n' + words[-1].capitalize()
                        else:
                            return operator
                    else:
                        return operator
            return text
        # Set colors
        header_color = colors.HexColor('#ff0000')  # Blue
        table_header_color = colors.HexColor('#0a8231')  # Green
        row_color = colors.HexColor('#ffffff')  # Light Gray
        text_color = colors.HexColor('#000000')  # Dark Blue

        # Shifts (headers)
        shift_headers = {
            'shift_1': '7h à 15h',
            'shift_2': '15h à 23h',
            'shift_3': '23h à 7h',
            'shift_4': '7h à 19h',
            'shift_5': '19h à 7h',
            'shift_6': '9h à 17h'
        }
        
        # --- BEGIN: Separate tables for model shift 1 and model shift 2 ---
        # Classify rows into model shift 1 (3 shifts) and model shift 2 (2 shifts)
        model1_shift_keys = ['shift_1', 'shift_2', 'shift_3']
        model2_shift_keys = ['shift_4', 'shift_5']
        model3_shift_keys = ['shift_6']
        model1_rows = []
        model2_rows = []
        model3_rows = []
        for row in schedule_data:
            if any(row[k] for k in model1_shift_keys):
                model1_rows.append(row)
            elif any(row[k] for k in model2_shift_keys):
                model2_rows.append(row)
            elif any(row[k] for k in model3_shift_keys):
                model3_rows.append(row)

        # Helper to render a table for a given set of rows and shift keys
        def render_table(page_obj, rows, shift_keys, shift_headers, y_offset=0):
            if not rows:
                return 0
            # Calculate dimensions for the table
            margin = 40
            available_width = page_width - (2 * margin)
            num_columns = len(shift_keys) + 1
            col_width = available_width / num_columns
            rows_per_page = 19
            row_height = min((page_height - 115) / (rows_per_page + 1), 60)
            # Prepare table data
            table_data = [['Machine'] + [shift_headers[k] for k in shift_keys]]
            for row in rows:
                machine_name = row['machine_name']
                article_name = row.get('article_name')
                article_abbr = row.get('article_abbreviation')
                if article_name and row.get('machine_type'):
                    display_article = article_name
                    if len(article_name) > 17 and article_abbr:
                        display_article = article_abbr
                    machine_name = f"{machine_name}\n({display_article})"
                table_row = [process_text(machine_name, is_machine=True)]
                for shift_key in shift_keys:
                    cell_text = row[shift_key] if row[shift_key] else ""
                    table_row.append(process_text(cell_text))
                table_data.append(table_row)
            # Choose fonts: Use Arial or Helvetica for header, table header, and first column
            # Fallback to Helvetica if Arial is not available in your ReportLab setup
            header_font = 'Helvetica-Bold'
            first_col_font = 'Helvetica-Bold'
            table_header_font = 'Helvetica-Bold'
            other_cells_font = bold_font_name  # Use your default for other cells, or set to 'Helvetica' if desired

            table = Table(
                table_data,
                colWidths=[col_width] * num_columns,
                rowHeights=[row_height] * len(table_data)
            )
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), table_header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), table_header_font),  # Table header row: Helvetica-Bold
                ('FONTNAME', (0, 1), (0, -1), first_col_font),     # First column (machines): Helvetica-Bold
                ('FONTNAME', (1, 1), (-1, -1), other_cells_font),  # Other cells: your default or Helvetica
                ('FONTSIZE', (0, 0), (-1, 0), 16),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 0),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
                ('FONTSIZE', (0, 1), (0, -1), 14),
                ('FONTSTYLE', (0, 1), (0, -1), 'UPPERCASE'),
                ('FONTSIZE', (1, 1), (-1, -1), 12 if name_type == 'latin' else 16),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ])
            for i in range(len(table_data)):
                if i % 2 == 1:
                    table_style.add('BACKGROUND', (0, i), (-1, i), row_color)
            table.setStyle(table_style)
            # Draw table
            table.wrapOn(page_obj, page_width, page_height)
            table_y = page_height - 50 - (len(table_data) * row_height) - y_offset
            table.drawOn(page_obj, margin, table_y)
            return (len(table_data) * row_height) + 30

        # --- END: Separate tables for model shift 1 and model shift 2 ---

        def add_page_footer(canvas, page_num, total_pages):
            # Add current date and time at the bottom center
            now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            canvas.setFont('Helvetica', 10)
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.drawCentredString(page_width / 2, 20, now)

        # Generate the page(s)
        p.setFont('Helvetica-Bold', 20)
        add_page_header(p, 1, 1)
        y_offset = 0
        if model1_rows:
            y_offset += render_table(p, model1_rows, model1_shift_keys, shift_headers, y_offset)
        if model2_rows:
            y_offset += render_table(p, model2_rows, model2_shift_keys, shift_headers, y_offset)
        if model3_rows:
            y_offset += render_table(p, model3_rows, model3_shift_keys, shift_headers, y_offset)
        add_page_footer(p, 1, 1)
        # Save the PDF
        p.save()
        # FileResponse
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        buffer.close()
        response.headers['Content-Type'] = 'application/pdf'
        name_suffix = 'ar' if name_type == 'arabic' else 'fr'
        response.headers['Content-Disposition'] = f'attachment; filename=emploi_{name_suffix}_semaine_{week}_{year}.pdf'

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500

def get_local_ip():
    #This method opens a connection to detect the local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        #Connect to an external IP without sending data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_user_accessible_pages(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT page_name, can_edit FROM user_accessible_pages WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            pages = cursor.fetchall()
            # Return as dict: {page_name: can_edit}
            return {page['page_name']: page['can_edit'] for page in pages}
    finally:
        connection.close()

def has_page_access(page, require_edit=False):
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True

   

    accessible_pages = get_user_accessible_pages(current_user.id)
    if page not in accessible_pages:
        return False
    if require_edit:
        return accessible_pages[page]
    return True

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

#Users Management
@app.route('/users')
@login_required
@admin_required
def users():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, username, email, role FROM users ORDER BY username"
            cursor.execute(sql)
            users = cursor.fetchall()
            # Get accessible pages for each user
            for user in users:
                user['accessible_pages'] = get_user_accessible_pages(user['id'])
        # Pass can_edit for the current user for the 'users' page
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('users', True) if current_user.role != 'admin' else True
    finally:
        connection.close()
    return render_template('users.html', users=users, can_edit=can_edit)

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    if not all(key in data for key in ['username', 'email', 'password', 'role']):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM users WHERE username = %s OR email = %s"
            cursor.execute(sql, (data['username'], data['email']))

            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username or email already exists'})
            sql = "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (
                data['username'],
                data['email'],
                generate_password_hash(data['password']),
                data['role']
            ))
            user_id = cursor.lastrowid
            # Add accessible pages with can_edit
            if 'accessible_pages' in data and data['accessible_pages']:
                sql = "INSERT INTO user_accessible_pages (user_id, page_name, can_edit) VALUES (%s, %s, %s)"
                for page in data['accessible_pages']:
                    if isinstance(page, dict):
                        cursor.execute(sql, (user_id, page['page_name'], page.get('can_edit', True)))
                    else:
                        cursor.execute(sql, (user_id, page, True))
            connection.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, username, email, role FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
            if user:
                user['accessible_pages'] = get_user_accessible_pages(user_id)
                return jsonify({'success': True, 'user': user})
            return jsonify({'success': False, 'message': 'User not found'})
    finally:
        connection.close()

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    data = request.get_json()
    
    if not all(key in data for key in ['username', 'email', 'role']):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if username or email exists for other users
            sql = "SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s"
            cursor.execute(sql, (data['username'], data['email'], user_id))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username or email already exists'})
            
            # Update user
            if 'password' in data and data['password']:
                sql = "UPDATE users SET username = %s, email = %s, password = %s, role = %s WHERE id = %s"
                cursor.execute(sql, (
                    data['username'],
                    data['email'],
                    generate_password_hash(data['password']),
                    data['role'],
                    user_id
                ))
            else:
                sql = "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s"
                cursor.execute(sql, (
                    data['username'],
                    data['email'],
                    data['role'],
                    user_id
                ))
            
            # Update accessible pages
            if 'accessible_pages' in data:
                # Delete existing pages
                sql = "DELETE FROM user_accessible_pages WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                
                # Add new pages
                if data['accessible_pages']:
                    sql = "INSERT INTO user_accessible_pages (user_id, page_name, can_edit) VALUES (%s, %s, %s)"
                    for page in data['accessible_pages']:
                        if isinstance(page, dict):
                            cursor.execute(sql, (user_id, page['page_name'], page.get('can_edit', True)))
                        else:
                            cursor.execute(sql, (user_id, page, True))
            
            connection.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    # Prevent deleting yourself
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete your own account'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Delete user (accessible pages will be deleted automatically due to CASCADE)
            sql = "DELETE FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            connection.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

# Daily Schedule History Functions
def save_daily_schedule_history(date_to_save=None):
    """Save the current schedule state for a specific date"""
    if date_to_save is None:
        date_to_save = datetime.now().date()
    
    # Calculate week and year for the date
    week = date_to_save.isocalendar()[1]
    year = date_to_save.year
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # First, delete any existing records for this date
            cursor.execute('''
                DELETE FROM daily_schedule_history 
                WHERE date_recorded = %s
            ''', (date_to_save,))
            
            # Get all current schedule assignments for this week
            cursor.execute('''
                SELECT 
                    s.machine_id, m.name as machine_name, 
                    s.production_id, p.article_id,
                    a.name as article_name, a.abbreviation as article_abbreviation,
                    s.operator_id, o.name as operator_name, 
                    s.shift_id, sh.name as shift_name, 
                    sh.start_time, sh.end_time,
                    s.position, s.week_number, s.year
                FROM schedule s
                JOIN machines m ON s.machine_id = m.id
                JOIN production p ON s.production_id = p.id
                LEFT JOIN articles a ON p.article_id = a.id
                JOIN operators o ON s.operator_id = o.id
                JOIN shifts sh ON s.shift_id = sh.id
                WHERE s.week_number = %s AND s.year = %s
                ORDER BY m.name, sh.start_time, s.position
            ''', (week, year))
            
            current_assignments = cursor.fetchall()
            
            # Ensure current_assignments is a list
            if current_assignments is None:
                current_assignments = []
            
            # Get completed productions from completed_productions table
            # Only include completed productions for the exact date they were completed
            cursor.execute('''
                SELECT 
                    cp.machine_id, cp.machine_name,
                    cp.production_id, cp.article_id,
                    cp.article_name, cp.article_abbreviation,
                    cp.operator_id, cp.operator_name,
                    cp.shift_id, cp.shift_name,
                    cp.shift_start_time as start_time, cp.shift_end_time as end_time,
                    cp.position, cp.week_number, cp.year
                FROM completed_productions cp
                WHERE DATE(cp.completion_date) = %s
                ORDER BY cp.machine_name, cp.shift_start_time, cp.position
            ''', (date_to_save,))
            
            completed_assignments = cursor.fetchall()
            
            # Ensure completed_assignments is a list
            if completed_assignments is None:
                completed_assignments = []
            
            # Get non-functioning machines that were reported today or recently
            cursor.execute('''
                SELECT DISTINCT m.id, m.name as machine_name, nfm.reported_date, nfm.issue, nfm.fixed_date
                FROM non_functioning_machines nfm
                JOIN machines m ON nfm.machine_id = m.id
                WHERE DATE(nfm.reported_date) = %s
                ORDER BY m.name
            ''', (date_to_save,))
            
            non_functioning_machines = cursor.fetchall()
            
            # Don't add any historical operators for NFM machines
            historical_assignments = []
            
            # Combine current, completed, and historical assignments
            all_assignments = list(current_assignments) + list(completed_assignments) + list(historical_assignments)
            
            # Group assignments by machine_name (case-insensitive, trimmed)
            from collections import defaultdict
            grouped_assignments = defaultdict(list)
            for assignment in all_assignments:
                machine_key = assignment['machine_name'].strip().lower()
                grouped_assignments[machine_key].append(assignment)
            

            
            # Insert each assignment into daily history
            for assignment in all_assignments:
                # Check if this assignment is completed
                is_completed = False
                if completed_assignments:
                    completed_keys = set()
                    for cp in completed_assignments:
                        completed_keys.add((
                            cp.get('machine_name', ''),
                            cp.get('operator_name', ''),
                            cp.get('shift_name', ''),
                            cp.get('start_time'),
                            cp.get('end_time'),
                            cp.get('position', 0),
                            cp.get('production_id', 0)
                        ))
                    
                    current_key = (
                        assignment.get('machine_name', ''),
                        assignment.get('operator_name', ''),
                        assignment.get('shift_name', ''),
                        assignment.get('start_time'),
                        assignment.get('end_time'),
                        assignment.get('position', 0),
                        assignment.get('production_id', 0)
                    )
                    is_completed = current_key in completed_keys
                
                cursor.execute('''
                    INSERT INTO daily_schedule_history (
                        date_recorded, week_number, year,
                        machine_id, production_id, operator_id, shift_id, position,
                        machine_name, operator_name, shift_name, shift_start_time, shift_end_time,
                        article_name, article_abbreviation, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    date_to_save, assignment.get('week_number', week), assignment.get('year', year),
                    assignment.get('machine_id'), assignment.get('production_id'), 
                    assignment.get('operator_id'), assignment.get('shift_id'), assignment.get('position', 0),
                    assignment['machine_name'], assignment['operator_name'], 
                    assignment['shift_name'], assignment['start_time'], assignment['end_time'],
                    assignment['article_name'], assignment['article_abbreviation'],
                    'completed' if is_completed else 'active'
                ))
            
            connection.commit()
            return True
    except Exception as e:
        print(f"Error saving daily history: {str(e)}")
        connection.rollback()
        return False
    finally:
        connection.close()

def get_daily_schedule_history(start_date=None, end_date=None):
    """Get daily schedule history for a date range"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if start_date and end_date:
                cursor.execute('''
                    SELECT DISTINCT date_recorded
                    FROM daily_schedule_history
                    WHERE date_recorded BETWEEN %s AND %s
                    ORDER BY date_recorded DESC
                ''', (start_date, end_date))
            else:
                cursor.execute('''
                    SELECT DISTINCT date_recorded
                    FROM daily_schedule_history
                    ORDER BY date_recorded DESC
                    LIMIT 30
                ''')
            
            dates = cursor.fetchall()
            history = {}
            
            for date_record in dates:
                date_recorded = date_record['date_recorded']
                
                # Get all assignments for this date from daily_schedule_history
                cursor.execute('''
                    SELECT DISTINCT
                        machine_name, operator_name, shift_name, 
                        shift_start_time, shift_end_time, article_name, article_abbreviation,
                        machine_id, production_id, operator_id, shift_id, position, status
                    FROM daily_schedule_history
                    WHERE date_recorded = %s
                    ORDER BY machine_name, shift_start_time, position
                ''', (date_recorded,))
                
                historical_assignments = cursor.fetchall()
                
                # ===== DEBUG 1 =====
                emballages_historical = [a for a in historical_assignments if a.get('machine_name') == 'EMBALLAGES']
                print(f"\n{date_recorded}: Historical - EMBALLAGES count: {len(emballages_historical)}")
                # ===== END DEBUG 1 =====
                
                # Determine if this date already has saved history entries
                has_saved_history_for_date = bool(historical_assignments)
                
                # Check if any machines have completed productions on or before this date
                cursor.execute('''
                    SELECT DISTINCT machine_id, machine_name
                    FROM completed_productions
                    WHERE DATE(completion_date) <= %s
                ''', (date_recorded,))
                
                completed_machines_before_date = cursor.fetchall()
                completed_machine_ids = {row['machine_id'] for row in completed_machines_before_date if row.get('machine_id')}
                completed_machine_names = {row['machine_name'] for row in completed_machines_before_date}
                
                # Filter out historical assignments for machines that completed production before this date
                filtered_historical_assignments = []
                for assignment in historical_assignments:
                    machine_id = assignment.get('machine_id')
                    machine_name = assignment.get('machine_name')
                    
                    # Check by machine_id OR machine_name
                    if (machine_id and machine_id in completed_machine_ids) or (machine_name in completed_machine_names):
                        # Check if this assignment is from the exact completion date
                        cursor.execute('''
                            SELECT COUNT(*) as count
                            FROM completed_productions
                            WHERE (machine_id = %s OR machine_name = %s) AND DATE(completion_date) = %s
                        ''', (machine_id, machine_name, date_recorded))
                        
                        completion_count = cursor.fetchone()['count']
                        if completion_count > 0:
                            # This is the completion date, so keep the assignment
                            filtered_historical_assignments.append(assignment)
                    else:
                        # Machine hasn't completed production, so keep the assignment
                        filtered_historical_assignments.append(assignment)
                
                historical_assignments = filtered_historical_assignments
                
                # ===== DEBUG 2 =====
                emballages_filtered = [a for a in historical_assignments if a.get('machine_name') == 'EMBALLAGES']
                print(f"{date_recorded}: After filtering - EMBALLAGES count: {len(emballages_filtered)}")
                # ===== END DEBUG 2 =====
                
                # Get current active assignments from schedule table (only active productions)
                current_assignments = []
                if not has_saved_history_for_date:
                    cursor.execute('''
                        SELECT 
                            m.name as machine_name, o.name as operator_name, s.name as shift_name,
                            s.start_time as shift_start_time, s.end_time as shift_end_time,
                            a.name as article_name, a.abbreviation as article_abbreviation,
                            m.id as machine_id, p.id as production_id, o.id as operator_id, s.id as shift_id, sch.position
                        FROM schedule sch
                        JOIN machines m ON sch.machine_id = m.id
                        JOIN production p ON sch.production_id = p.id
                        LEFT JOIN articles a ON p.article_id = a.id
                        JOIN operators o ON sch.operator_id = o.id
                        JOIN shifts s ON sch.shift_id = s.id
                        WHERE sch.week_number = %s AND sch.year = %s
                        AND p.status = 'active'
                        ORDER BY m.name, s.start_time, sch.position
                    ''', (date_recorded.isocalendar()[1], date_recorded.year))
                    
                    current_assignments = cursor.fetchall()
                
                # ===== DEBUG 3 =====
                emballages_current = [a for a in current_assignments if a.get('machine_name') == 'EMBALLAGES']
                print(f"{date_recorded}: Current assignments - EMBALLAGES count: {len(emballages_current)}")
                # ===== END DEBUG 3 =====
                
                # Get completed assignments from completed_productions table
                cursor.execute('''
                    SELECT 
                        cp.machine_name, cp.operator_name, cp.shift_name,
                        cp.shift_start_time, cp.shift_end_time,
                        cp.article_name, cp.article_abbreviation,
                        cp.machine_id, cp.production_id, cp.operator_id, cp.shift_id, cp.position
                    FROM completed_productions cp
                    WHERE DATE(cp.completion_date) = %s
                    ORDER BY cp.machine_name, cp.shift_start_time, cp.position
                ''', (date_recorded,))
                
                completed_assignments = cursor.fetchall()
                
                # Filter out machines that have completed productions from current_assignments
                if completed_assignments:
                    completed_machine_ids = {assignment['machine_id'] for assignment in completed_assignments if assignment.get('machine_id')}
                    completed_machine_names = {assignment['machine_name'] for assignment in completed_assignments}
                    
                    if completed_machine_ids or completed_machine_names:
                        current_assignments = [
                            assignment for assignment in current_assignments 
                            if (assignment.get('machine_id') not in completed_machine_ids 
                                and assignment.get('machine_name') not in completed_machine_names)
                        ]
                
                # ===== DEBUG 4 =====
                emballages_current_after = [a for a in current_assignments if a.get('machine_name') == 'EMBALLAGES']
                print(f"{date_recorded}: Current after completed filter - EMBALLAGES count: {len(emballages_current_after)}")
                # ===== END DEBUG 4 =====
                
                # Combine all assignments with deduplication
                assignments = []
                seen_assignments = set()
                
                def get_assignment_key(assignment):
                    return (
                        assignment.get('machine_name', ''),
                        assignment.get('operator_name', ''),
                        assignment.get('shift_name', ''),
                        assignment.get('shift_start_time'),
                        assignment.get('shift_end_time'),
                        assignment.get('position', 0),
                        assignment.get('production_id', 0)
                    )
                
                # Add assignments with deduplication
                for assignment_list in [historical_assignments, current_assignments, completed_assignments]:
                    if assignment_list:
                        for assignment in assignment_list:
                            key = get_assignment_key(assignment)
                            if key not in seen_assignments:
                                seen_assignments.add(key)
                                if assignment_list is completed_assignments:
                                    assignment['status'] = 'completed'
                                assignments.append(assignment)
                
                # ===== DEBUG 5 =====
                emballages_combined = [a for a in assignments if a.get('machine_name') == 'EMBALLAGES']
                print(f"{date_recorded}: Combined assignments - EMBALLAGES count: {len(emballages_combined)}")
                # ===== END DEBUG 5 =====
                
                # Get non-functioning machines for this date
                week = date_recorded.isocalendar()[1]
                year = date_recorded.year
                
                cursor.execute('''
                    SELECT 
                        m.name as machine_name,
                        m.id as machine_id,
                        nfm.reported_date,
                        nfm.issue,
                        nfm.fixed_date,
                        m.status as current_status
                    FROM non_functioning_machines nfm
                    JOIN machines m ON nfm.machine_id = m.id
                    WHERE (DATE(nfm.reported_date) = %s OR DATE(nfm.fixed_date) = %s)
                       OR (DATE(nfm.reported_date) = %s AND nfm.fixed_date IS NULL)
                       OR (m.status = 'broken' AND DATE(nfm.reported_date) <= %s)
                    ORDER BY m.name, nfm.reported_date
                ''', (date_recorded, date_recorded, date_recorded - timedelta(days=1), date_recorded))
                
                all_nfm_machines = cursor.fetchall()
                
                # Filter to only include NFM machines that were in production this week
                base_nfm_machines = []
                for nfm in all_nfm_machines:
                    cursor.execute('''
                        SELECT COUNT(*) as count
                        FROM production p
                        WHERE p.machine_id = %s 
                        AND p.status = 'active'
                        AND p.start_date <= %s
                        AND (p.end_date IS NULL OR p.end_date >= %s)
                    ''', (nfm['machine_id'], date_recorded, date_recorded))
                    
                    count_result = cursor.fetchone()
                    if count_result and count_result['count'] > 0:
                        base_nfm_machines.append(nfm)
                
                # Group NFM events by machine
                nfm_by_machine = {}
                for nfm in base_nfm_machines:
                    machine_id = nfm['machine_id']
                    if machine_id not in nfm_by_machine:
                        nfm_by_machine[machine_id] = []
                    nfm_by_machine[machine_id].append(nfm)
                
                # Process NFM notifications
                non_functioning_machines = []
                for machine_id, nfm_events in nfm_by_machine.items():
                    nfm_events.sort(key=lambda x: x['reported_date'])
                    
                    current_date_events = [e for e in nfm_events if e['reported_date'].date() == date_recorded]
                    previous_date_events = [e for e in nfm_events if e['reported_date'].date() == date_recorded - timedelta(days=1)]
                    
                    if current_date_events:
                        for event in current_date_events:
                            non_functioning_machines.append(event)
                    elif previous_date_events and any(e['current_status'] == 'broken' for e in previous_date_events):
                        latest_previous = max(previous_date_events, key=lambda x: x['reported_date'])
                        if latest_previous['current_status'] == 'broken':
                            non_functioning_machines.append(latest_previous)
                
                # Structure: {machine: [{operator, shift, start_time, end_time, article}]}
                day_data = {}
                for assignment in assignments:
                    machine = assignment['machine_name']
                    if machine not in day_data:
                        day_data[machine] = []
                    
                    article_info = ""
                    if assignment['article_name']:
                        article_info = assignment['article_abbreviation'] or assignment['article_name']
                    
                    is_historical = assignment.get('machine_id') is None
                    is_completed = assignment.get('status') == 'completed'
                    
                    day_data[machine].append({
                        'operator': assignment['operator_name'],
                        'shift': assignment['shift_name'],
                        'start_time': str(assignment['shift_start_time']),
                        'end_time': str(assignment['shift_end_time']),
                        'article': article_info,
                        'is_historical': is_historical,
                        'is_completed': is_completed
                    })
                
                # ===== DEBUG 6 =====
                if 'EMBALLAGES' in day_data:
                    print(f"✅ {date_recorded}: EMBALLAGES in day_data with {len(day_data['EMBALLAGES'])} items")
                else:
                    print(f"❌ {date_recorded}: EMBALLAGES NOT in day_data")
                    print(f"   day_data keys: {list(day_data.keys())}")
                # ===== END DEBUG 6 =====
                
                # Add non-functioning machines to the day data
                for nfm in non_functioning_machines:
                    machine = nfm['machine_name']
                    if machine not in day_data:
                        day_data[machine] = []
                    
                    reported_time = nfm['reported_date'].strftime('%H:%M') if nfm['reported_date'] else ''
                    
                    is_fixed_on_this_date = nfm['fixed_date'] and nfm['fixed_date'].date() == date_recorded
                    is_reported_on_this_date = nfm['reported_date'] and nfm['reported_date'].date() == date_recorded
                    is_from_previous_day = nfm['reported_date'] and nfm['reported_date'].date() == date_recorded - timedelta(days=1)
                    
                    if is_fixed_on_this_date:
                        fixed_time = nfm['fixed_date'].strftime('%H:%M') if nfm['fixed_date'] else ''
                        day_data[machine].append({
                            'operator': 'Machine réparée',
                            'shift': 'Réparée',
                            'start_time': reported_time,
                            'end_time': fixed_time,
                            'start_date': nfm['fixed_date'].strftime('%Y-%m-%d') if nfm['fixed_date'] else '',
                            'end_date': nfm['fixed_date'].strftime('%Y-%m-%d') if nfm['fixed_date'] else '',
                            'article': f"{nfm['issue'] or 'Panne signalée'} (Réparée)",
                            'is_non_functioning': True,
                            'is_repaired': True
                        })
                    elif is_reported_on_this_date:
                        day_data[machine].append({
                            'operator': 'Machine en panne',
                            'shift': 'Non fonctionnelle',
                            'start_time': reported_time,
                            'end_time': '',
                            'start_date': nfm['reported_date'].strftime('%Y-%m-%d') if nfm['reported_date'] else '',
                            'end_date': nfm['reported_date'].strftime('%Y-%m-%d') if nfm['reported_date'] else '',
                            'article': nfm['issue'] or 'Panne signalée',
                            'is_non_functioning': True
                        })
                    elif is_from_previous_day and nfm['current_status'] == 'broken':
                        day_data[machine].append({
                            'operator': 'Machine en panne',
                            'shift': 'Non fonctionnelle',
                            'start_time': reported_time,
                            'end_time': '',
                            'start_date': nfm['reported_date'].strftime('%Y-%m-%d') if nfm['reported_date'] else '',
                            'end_date': nfm['reported_date'].strftime('%Y-%m-%d') if nfm['reported_date'] else '',
                            'article': nfm['issue'] or 'Panne signalée',
                            'is_non_functioning': True
                        })
                
                # Use date as key (YYYY-MM-DD format)
                key = date_recorded.strftime('%Y-%m-%d')
                history[key] = day_data
            
            # ===== FINAL DEBUG =====
            print(f"\n{'='*60}")
            print(f"FINAL HISTORY - Total dates: {len(history)}")
            for date_key, machines in history.items():
                if 'EMBALLAGES' in machines:
                    print(f"✅ {date_key}: EMBALLAGES with {len(machines['EMBALLAGES'])} assignments")
                else:
                    print(f"❌ {date_key}: EMBALLAGES NOT FOUND")
            print(f"{'='*60}\n")
            # ===== END FINAL DEBUG =====
            
            return history
    finally:
        connection.close()

def get_schedule_history():
    """Get weekly schedule history (for backward compatibility)"""
    return get_daily_schedule_history()

@app.route('/history')
@login_required
def history():
    ensure_today_history()
    # Get date range from query parameters (default to last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Allow custom date range
    if request.args.get('start_date'):
        try:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if request.args.get('end_date'):
        try:
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    history_data = get_daily_schedule_history(start_date, end_date)
    # --- Add for modal ---
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM articles ORDER BY name")
            articles = cursor.fetchall()
            cursor.execute("SELECT * FROM machines WHERE status = 'operational' ORDER BY name")
            machines = cursor.fetchall()
        current_access = get_user_accessible_pages(current_user.id)
        can_edit = current_access.get('production', True) if current_user.role != 'admin' else True
    finally:
        connection.close()
    # --- End add ---
    return render_template('history.html', history=history_data, start_date=start_date, end_date=end_date, machines=machines, articles=articles, can_edit=can_edit)

@app.route('/api/save_today_history', methods=['POST'])
@login_required
@admin_required
def save_today_history():
    """Save today's schedule to daily history"""
    try:
        success = save_daily_schedule_history()
        if success:
            return jsonify({'success': True, 'message': 'Today\'s schedule saved to history.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save today\'s schedule.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/save_daily_history', methods=['POST'])
@login_required
@admin_required
def save_daily_history():
    """Save schedule for a specific date to daily history"""
    data = request.get_json()
    date_str = data.get('date')
    
    if not date_str:
        return jsonify({'success': False, 'message': 'Date is required'})
    
    try:
        date_to_save = datetime.strptime(date_str, '%Y-%m-%d').date()
        success = save_daily_schedule_history(date_to_save)
        if success:
            return jsonify({'success': True, 'message': f'Schedule for {date_str} saved to history.'})
        else:
            return jsonify({'success': False, 'message': f'Failed to save schedule for {date_str}.'})
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/daily_history', methods=['GET'])
@login_required
def get_daily_history_api():
    """Get daily history for a date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        history_data = get_daily_schedule_history(start_date_obj, end_date_obj)
        return jsonify({'success': True, 'history': history_data})
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#Ensure Today History is saved in the database
def ensure_today_history():
    today = datetime.now().date()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM daily_schedule_history WHERE date_recorded = %s LIMIT 1", (today,))
            if not cursor.fetchone():
                # Get the most recent previous day with history
                cursor.execute("SELECT date_recorded FROM daily_schedule_history WHERE date_recorded < %s ORDER BY date_recorded DESC LIMIT 1", (today,))
                last = cursor.fetchone()
                if last:
                    last_date = last['date_recorded']
                    last_week, last_year = last_date.isocalendar()[1], last_date.year
                    this_week, this_year = today.isocalendar()[1], today.year
                    same_iso_week = (last_week == this_week) and (last_year == this_year)
                    if same_iso_week:
                        # Same week: copy active rows
                        cursor.execute("SELECT * FROM daily_schedule_history WHERE date_recorded = %s AND status = 'active'", (last_date,))
                        rows = cursor.fetchall()
                        for row in rows:
                            row_data = dict(row)
                            row_data['date_recorded'] = today
                            row_data.pop('id', None)
                            columns = ', '.join(row_data.keys())
                            placeholders = ', '.join(['%s'] * len(row_data))
                            cursor.execute(f"INSERT INTO daily_schedule_history ({columns}) VALUES ({placeholders})", tuple(row_data.values()))
                        connection.commit()
                    else:
                        # New week: if a program exists for the new week, snapshot it; otherwise copy the last day's active rows
                        cursor.execute('''
                            SELECT COUNT(*) AS cnt
                            FROM schedule sch
                            JOIN production p ON sch.production_id = p.id
                            WHERE sch.week_number = %s AND sch.year = %s AND p.status = 'active'
                        ''', (this_week, this_year))
                        week_has_program = (cursor.fetchone() or {}).get('cnt', 0) > 0
                        if week_has_program:
                            # Snapshot today's schedule into history for the new week start
                            # Commit any prior reads first to keep connection clean
                            connection.commit()
                            save_daily_schedule_history(today)
                        else:
                            # No program for the new week yet → copy active rows from last recorded day (typically Sunday)
                            cursor.execute("SELECT * FROM daily_schedule_history WHERE date_recorded = %s AND status = 'active'", (last_date,))
                            rows = cursor.fetchall()
                            for row in rows:
                                row_data = dict(row)
                                row_data['date_recorded'] = today
                                row_data.pop('id', None)
                                columns = ', '.join(row_data.keys())
                                placeholders = ', '.join(['%s'] * len(row_data))
                                cursor.execute(f"INSERT INTO daily_schedule_history ({columns}) VALUES ({placeholders})", tuple(row_data.values()))
                            connection.commit()
                
                # Also ensure today has any non-functioning machine events that were saved directly
                # Check if there are any non-functioning machine events for today that weren't copied
                cursor.execute("""
                    SELECT nfm.*, m.name as machine_name 
                    FROM non_functioning_machines nfm 
                    JOIN machines m ON nfm.machine_id = m.id 
                    WHERE DATE(nfm.reported_date) = %s
                """, (today,))
                nfm_events = cursor.fetchall()
                
                for event in nfm_events:
                    # Check if this event is already in history
                    cursor.execute("""
                        SELECT 1 FROM daily_schedule_history 
                        WHERE date_recorded = %s AND machine_name = %s 
                        AND operator_name = 'Machine en panne' AND article_name = %s
                    """, (today, event['machine_name'], event['issue']))
                    
                    if not cursor.fetchone():
                        # Add non-functioning notification to history
                        reported_time = event['reported_date'].strftime('%H:%M') if event['reported_date'] else ''
                        week = today.isocalendar()[1]
                        year = today.year
                        
                        cursor.execute('''
                            INSERT INTO daily_schedule_history (
                                date_recorded, week_number, year,
                                machine_id, production_id, operator_id, shift_id, position,
                                machine_name, operator_name, shift_name, shift_start_time, shift_end_time,
                                article_name, article_abbreviation, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            today, week, year,
                            None, None, None, None, 0,
                            event['machine_name'], 'Machine en panne', 'Non fonctionnelle', 
                            reported_time, '', event['issue'] or 'Panne signalée', '', 'active'
                        ))
                
                # Check for repair events for today
                cursor.execute("""
                    SELECT nfm.*, m.name as machine_name 
                    FROM non_functioning_machines nfm 
                    JOIN machines m ON nfm.machine_id = m.id 
                    WHERE DATE(nfm.fixed_date) = %s AND nfm.fixed_date IS NOT NULL
                """, (today,))
                repair_events = cursor.fetchall()
                
                for event in repair_events:
                    # Check if this repair event is already in history
                    cursor.execute("""
                        SELECT 1 FROM daily_schedule_history 
                        WHERE date_recorded = %s AND machine_name = %s 
                        AND operator_name = 'Machine réparée' AND article_name = %s
                    """, (today, event['machine_name'], event['issue']))
                    
                    if not cursor.fetchone():
                        # Add repair notification to history
                        fixed_time = event['fixed_date'].strftime('%H:%M') if event['fixed_date'] else ''
                        week = today.isocalendar()[1]
                        year = today.year
                        
                        cursor.execute('''
                            INSERT INTO daily_schedule_history (
                                date_recorded, week_number, year,
                                machine_id, production_id, operator_id, shift_id, position,
                                machine_name, operator_name, shift_name, shift_start_time, shift_end_time,
                                article_name, article_abbreviation, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            today, week, year,
                            None, None, None, None, 1,
                            event['machine_name'], 'Machine réparée', 'Fonctionnelle', 
                            fixed_time, '', event['issue'] or 'Panne réparée', '', 'active'
                        ))
                
                connection.commit()
    finally:
        connection.close()

@app.route('/api/postes', methods=['GET'])
@login_required
def get_postes():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, name, type FROM postes ORDER BY name"
            cursor.execute(sql)
            postes = cursor.fetchall()
            return jsonify({'success': True, 'postes': postes})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()
@app.route('/api/machines/<int:machine_id>/poste')
@login_required
def get_machine_poste_api(machine_id):
    connection = get_db_connection()
    try:
        poste = get_machine_poste(machine_id, connection)
        return jsonify({'success': True, 'poste': poste})
    finally:
        connection.close()

@app.route('/api/machines', methods=['GET'])
@login_required
def get_machines():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT m.*, p.name as poste_name, p.type as poste_type
                FROM machines m
                LEFT JOIN postes p ON m.poste_id = p.id
                ORDER BY m.status
            """
            cursor.execute(sql)
            machines = cursor.fetchall()
        return jsonify({'success': True, 'machines': machines})
    finally:
        connection.close()

@app.route('/api/operators/<int:operator_id>', methods=['DELETE'])
@login_required
def delete_operator(operator_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if operator has active absences
            sql = "SELECT id FROM absences WHERE operator_id = %s"
            cursor.execute(sql, (operator_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Cannot delete operator with active absences'})
            
            # Check if operator is used in schedule
            sql = "SELECT id FROM schedule WHERE operator_id = %s"
            cursor.execute(sql, (operator_id,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Cannot delete operator that is used in schedule'})
            
            # Delete operator
            sql = "DELETE FROM operators WHERE id = %s"
            cursor.execute(sql, (operator_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Operator deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        connection.close()

@app.route('/export_history', methods=['GET'])
@login_required
def export_history():
    date_str = request.args.get('date')
    name_type = request.args.get('name_type', 'latin')

    if not date_str:
        return jsonify({"error": "Date parameter is required"}), 400

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all shifts
        cursor.execute('SELECT id, name, start_time, end_time FROM shifts ORDER BY id')
        shifts = cursor.fetchall()
        shift_id_to_key = {s['id']: f'shift_{s["id"]}' for s in shifts}
        def format_shift_time(start, end):
            def extract_hour(t):
                t_str = str(t)
                if ':' in t_str:
                    hour_part = t_str.split(':')[0]
                    try:
                        return f"{int(hour_part)}h"
                    except Exception:
                        return t_str
                try:
                    return f"{int(t_str)}h"
                except Exception:
                    return t_str
            start_h = extract_hour(start)
            end_h = extract_hour(end)
            return f"{start_h} à {end_h}"
        shift_headers = {f'shift_{s["id"]}': format_shift_time(s['start_time'], s['end_time']) for s in shifts}
        shift_keys = [f'shift_{s["id"]}' for s in shifts]

        # Get all non-functioning machines for this date
        cursor.execute('''
            SELECT m.id
            FROM non_functioning_machines nfm
            JOIN machines m ON nfm.machine_id = m.id
            WHERE DATE(nfm.reported_date) = %s
            AND (nfm.fixed_date IS NULL OR DATE(nfm.fixed_date) > %s)
        ''', (date_obj, date_obj))
        non_functioning_ids = set(row['id'] for row in cursor.fetchall())

        # Get machines that were NFM on the previous day and weren't repaired
        previous_date = date_obj - timedelta(days=1)
        cursor.execute('''
            SELECT m.id
            FROM non_functioning_machines nfm
            JOIN machines m ON nfm.machine_id = m.id
            WHERE DATE(nfm.reported_date) = %s
            AND (nfm.fixed_date IS NULL OR DATE(nfm.fixed_date) > %s)
        ''', (previous_date, date_obj))
        previous_nfm_ids = set(row['id'] for row in cursor.fetchall())

        # Combine both sets of non-functioning machine IDs
        all_non_functioning_ids = non_functioning_ids.union(previous_nfm_ids)

        # Get all assignments for the day, but filter out non-functioning, historical, and completed productions
        if name_type == 'arabic':
            cursor.execute('''
                SELECT 
                    d.machine_id,
                    d.machine_name,
                    m.type as machine_type,
                    d.article_name,
                    d.article_abbreviation,
                    d.shift_id,
                    o.arabic_name as operator_name
                FROM daily_schedule_history d
                LEFT JOIN machines m ON d.machine_id = m.id
                LEFT JOIN operators o ON d.operator_name = o.name
                LEFT JOIN production p ON d.production_id = p.id
                WHERE d.date_recorded = %s
                AND m.status != 'broken'
                AND d.machine_id IS NOT NULL
                AND (p.status IS NULL OR p.status = 'active')
                ORDER BY d.machine_name, d.article_name, d.shift_id
            ''', (date_obj,))
        else:
            cursor.execute('''
                SELECT 
                    d.machine_id,
                    d.machine_name,
                    m.type as machine_type,
                    d.article_name,
                    d.article_abbreviation,
                    d.shift_id,
                    d.operator_name
                FROM daily_schedule_history d
                LEFT JOIN machines m ON d.machine_id = m.id
                LEFT JOIN production p ON d.production_id = p.id
                WHERE d.date_recorded = %s
                AND m.status != 'broken'
                AND d.machine_id IS NOT NULL
                AND (p.status IS NULL OR p.status = 'active')
                ORDER BY d.machine_name, d.article_name, d.shift_id
            ''', (date_obj,))
        assignments = [row for row in cursor.fetchall() if row['machine_id'] not in all_non_functioning_ids]
        conn.close()
        # Collect all unique (machine_name, article_name, article_abbreviation, machine_type)
        machine_article_keys = []
        machine_article_map = {}  # (machine_name, article_name, article_abbreviation, machine_type) -> {shift_key: operator_name}
        for row in assignments:
            m = row['machine_name']
            article = row['article_name']
            abbr = row['article_abbreviation']
            mtype = row.get('machine_type', 0)
            key = (m, article, abbr, mtype)
            s = shift_id_to_key[row['shift_id']]
            op = row['operator_name']
            if key not in machine_article_map:
                machine_article_map[key] = {}
                machine_article_keys.append(key)
            # Handle multiple operators for the same machine/shift combination
            if s in machine_article_map[key]:
                # If there's already an operator, append with comma separator
                machine_article_map[key][s] = machine_article_map[key][s] + ', ' + op
            else:
                machine_article_map[key][s] = op

        # Prepare rows for the PDF
        model1_shift_keys = ['shift_1', 'shift_2', 'shift_3']
        model2_shift_keys = ['shift_4', 'shift_5']
        model3_shift_keys = ['shift_6']
        model1_rows = []
        model2_rows = []
        model3_rows = []
        for key in sorted(machine_article_keys):
            m, article, abbr, mtype = key
            row_dict = {
                'machine_name': m,
                'machine_type': mtype,
                'article_name': article,
                'article_abbreviation': abbr,
            }
            for k in shift_keys:
                row_dict[k] = machine_article_map[key].get(k, '')
            # Assign to model
            if any(row_dict[k] for k in model1_shift_keys):
                model1_rows.append(row_dict)
            elif any(row_dict[k] for k in model2_shift_keys):
                model2_rows.append(row_dict)
            elif any(row_dict[k] for k in model3_shift_keys):
                model3_rows.append(row_dict)
        model1_rows.sort(key=lambda row: (row.get('machine_type') == 1, row.get('machine_name', '')))
        model2_rows.sort(key=lambda row: (row.get('machine_type') == 1, row.get('machine_name', '')))
        model3_rows.sort(key=lambda row: (row.get('machine_type') == 1, row.get('machine_name', '')))

        # PDF generation (same as export_sch)
        buffer = BytesIO()
        page_width, page_height = portrait(A4)
        p = canvas.Canvas(buffer, pagesize=portrait(A4))

        try:
            if name_type == 'arabic' or (lang if 'lang' in locals() else None) == 'ar':
                font_name = 'Amiri'
                bold_font_name = 'Amiri'
            else:
                font_name = 'Amiri'
                bold_font_name = 'Amiri'
            font_paths = [
                '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
                '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
                'static/fonts/Amiri-Regular.ttf'
            ]
            bold_font_paths = [
                'static/fonts/Amiri-Bold.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
            font_found = False
            for path in font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arabic', path))
                    font_name = 'Arabic'
                    font_found = True
                    break
            if not font_found:
                pdfmetrics.registerFont(TTFont('Arabic', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                font_name = 'Arabic'
            bold_font_found = False
            for path in bold_font_paths:
                if os.path.exists(path):
                    pdfmetrics.registerFont(TTFont('Arabic-Bold', path))
                    bold_font_name = 'Arabic-Bold'
                    bold_font_found = True
                    break
            if not bold_font_found:
                bold_font_name = font_name
        except Exception as e:
            print(f"Font registration error: {str(e)}")
            font_name = 'Helvetica'
            bold_font_name = 'Helvetica-Bold'

        # --- Helvetica font override for header, table header, machine names, and first row ---
        helvetica_font = 'Helvetica'
        helvetica_bold_font = 'Helvetica-Bold'

        def add_page_header(canvas, page_num, total_pages):
            # Use Helvetica for page header
            canvas.setFont(helvetica_bold_font, 20)
            canvas.setFillColor(colors.HexColor('#ff0000'))
            title_text = "Programme"
            header_text = f"{title_text} {date_obj.strftime('%d/%m/%Y')}"
            y = page_height - 40
            canvas.drawCentredString(page_width / 2, y, header_text)

        def process_text(text, is_header=False, is_machine=False):
            if not text:
                return ""
            text = str(text)
            
            if is_header:
                return text
            
            if name_type == 'arabic' and any(ord(char) in range(0x0600, 0x06FF) for char in text):
                if not is_machine:
                    operators = text.split(',')
                    if len(operators) > 1:
                        processed_operators = []
                        for operator in operators:
                            operator = operator.strip()
                            if len(operator) > 20:
                                words = operator.split()
                                if len(words) > 1:
                                    processed_operators.append(' '.join(words[:-1]) + '\n' + words[-1])
                                else:
                                    processed_operators.append(operator)
                            else:
                                processed_operators.append(operator)
                        text = '\n+ '.join(processed_operators)
                    else:
                        operator = text.strip()
                        if len(operator) > 20:
                            words = operator.split()
                            if len(words) > 1:
                                text = ' '.join(words[:-1]) + '\n' + words[-1]
                            else:
                                text = operator
                        else:
                            text = operator
                reshaped_text = arabic_reshaper.reshape(text)
                return get_display(reshaped_text)
            elif is_machine:
                return text.upper()
            elif not is_header:
                operators = text.split(',')
                if len(operators) > 1:
                    processed_operators = []
                    for operator in operators:
                        operator = operator.strip()
                        operator_cap = operator.capitalize()
                        if len(operator_cap) > 20:
                            words = operator_cap.split()
                            if len(words) > 1:
                                processed_operators.append(' '.join(words[:-1]) + '\n' + words[-1].capitalize())
                            else:
                                processed_operators.append(operator_cap)
                        else:
                            processed_operators.append(operator_cap)
                    return '\n+ '.join(processed_operators)
                else:
                    operator = text.strip().capitalize()
                    if len(operator) > 20:
                        words = operator.split()
                        if len(words) > 1:
                            return ' '.join(words[:-1]) + '\n' + words[-1].capitalize()
                        else:
                            return operator
                    else:
                        return operator
            return text

        def render_table(page_obj, rows, shift_keys, shift_headers, y_offset=0):
            if not rows:
                return 0
            margin = 40
            available_width = page_width - (2 * margin)
            num_columns = len(shift_keys) + 1
            col_width = available_width / num_columns
            rows_per_page = 19
            row_height = min((page_height - 115) / (rows_per_page + 1), 60)
            table_data = [['Machine'] + [shift_headers[k] for k in shift_keys]]
            for row in rows:
                machine_name = row['machine_name']
                article_name = row.get('article_name')
                article_abbr = row.get('article_abbreviation')
                if article_name and row.get('machine_type'):
                    display_article = article_name
                    if len(article_name) > 17 and article_abbr:
                        display_article = article_abbr
                    machine_name = f"{machine_name}\n({display_article})"
                table_row = [process_text(machine_name, is_machine=True)]
                for shift_key in shift_keys:
                    cell_text = row[shift_key] if row[shift_key] else ""
                    table_row.append(process_text(cell_text))
                table_data.append(table_row)
            from reportlab.platypus import Table, TableStyle
            table = Table(
                table_data,
                colWidths=[col_width] * num_columns,
                rowHeights=[row_height] * len(table_data)
            )
            # TableStyle: Helvetica for table header, machine names, and first row
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0a8231')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                # Table header row (row 0): Helvetica-Bold
                ('FONTNAME', (0, 0), (-1, 0), helvetica_bold_font),
                ('FONTNAME', (0, 1), (0, -1), helvetica_bold_font),
                ('FONTNAME', (1, 1), (-1, -1), bold_font_name),
                # Other cells: fallback to font_name (Amiri/Arabic/Helvetica)
                ('FONTNAME', (1, 2), (-1, -1), bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 0),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#000000')),
                ('FONTSIZE', (0, 1), (0, -1), 12),
                ('FONTSIZE', (1, 1), (-1, -1), 10 if name_type == 'latin' else 15),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ])
            for i in range(len(table_data)):
                if i % 2 == 1:
                    table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffffff'))
            table.setStyle(table_style)
            table.wrapOn(page_obj, page_width, page_height)
            table_y = page_height - 50 - (len(table_data) * row_height) - y_offset
            table.drawOn(page_obj, margin, table_y)
            return (len(table_data) * row_height) + 30

        def add_page_footer(canvas, page_num, total_pages):
            now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            # Use Helvetica for footer for consistency (optional)
            canvas.setFont(helvetica_font, 10)
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.drawCentredString(page_width / 2, 20, now)

        p.setFont(helvetica_bold_font, 20)
        add_page_header(p, 1, 1)
        y_offset = 0
        if model1_rows:
            y_offset += render_table(p, model1_rows, model1_shift_keys, shift_headers, y_offset)
        if model2_rows:
            y_offset += render_table(p, model2_rows, model2_shift_keys, shift_headers, y_offset)
        if model3_rows:
            y_offset += render_table(p, model3_rows, model3_shift_keys, shift_headers, y_offset)
        add_page_footer(p, 1, 1)
        p.save()
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        buffer.close()
        response.headers['Content-Type'] = 'application/pdf'
        name_suffix = 'ar' if name_type == 'arabic' else 'fr'
        response.headers['Content-Disposition'] = f'attachment; filename=emploi_{name_suffix}_jour_{date_str}.pdf'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500

#Split Production - When an article is changed, the production is split into two
#Production status is set to completed for the old production
#And a new production is created with the new article and quantity
@app.route('/api/schedule/split_production', methods=['POST'])
@login_required
def split_production():
    data = request.get_json()
    production_id = data.get('production_id')
    machine_id = data.get('machine_id')
    article_id = data.get('article_id')
    quantity = data.get('quantity')
    start_date = data.get('start_date')  # new start date (should be today)
    end_date = data.get('end_date')      # new end date (optional)
    hour_start = data.get('hour_start')  # new hour start (optional)
    hour_end = data.get('hour_end')      # new hour end (optional)
    status = data.get('status', 'active')

    if not production_id or not machine_id or not start_date:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if not end_date:
        end_date = None

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Get the current production record
            cursor.execute("SELECT * FROM production WHERE id = %s", (production_id,))
            prod = cursor.fetchone()
            if not prod:
                return jsonify({'success': False, 'message': 'Production not found'}), 404

            old_machine_id = prod['machine_id']
            old_article_id = prod['article_id']
            old_quantity = prod['quantity']
            old_status = prod['status']
            old_start_date = prod['start_date']
            old_end_date = prod['end_date']

            # Check what changed
            machine_changed = str(machine_id) != str(old_machine_id)
            article_changed = str(article_id) != str(old_article_id)

            if article_changed:
                # Article changed: mark old production as completed and create new one
                today = datetime.strptime(start_date, '%Y-%m-%d').date()
                yesterday = today - timedelta(days=1)
                cursor.execute(
                    "UPDATE production SET end_date = %s, status = 'completed' WHERE id = %s",
                    (yesterday.strftime('%Y-%m-%d'), production_id)
                )
                
                # Save completed production to history
                save_completed_production_to_history(production_id, yesterday.strftime('%Y-%m-%d'))

                # 3. Insert the new production starting today
                insert_sql = """
                    INSERT INTO production (machine_id, article_id, quantity, start_date, end_date, hour_start, hour_end, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql,
                    (machine_id, article_id, quantity, start_date, end_date, hour_start, hour_end, status)
                )
                new_production_id = cursor.lastrowid

                # 4. Copy schedule assignments for the current week from old machine/production to new machine/production
                week_number = datetime.strptime(start_date, '%Y-%m-%d').date().isocalendar()[1]
                year = datetime.strptime(start_date, '%Y-%m-%d').date().year

                copy_schedule_sql = """
                    INSERT INTO schedule (machine_id, production_id, operator_id, shift_id, position, week_number, year)
                    SELECT %s, %s, operator_id, shift_id, position, week_number, year
            FROM schedule
                    WHERE machine_id = %s AND production_id = %s AND week_number = %s AND year = %s
                """
                cursor.execute(
                    copy_schedule_sql,
                    (machine_id, new_production_id, old_machine_id, production_id, week_number, year)
                )

                # 5. Delete old assignments for this week (move, not copy)
                delete_old_sql = """
                    DELETE FROM schedule
                    WHERE machine_id = %s AND production_id = %s AND week_number = %s AND year = %s
                """
                cursor.execute(
                    delete_old_sql,
                    (old_machine_id, production_id, week_number, year)
                )

                connection.commit()
                return jsonify({'success': True, 'message': 'Production split and new production created successfully (article changed)'})
            elif machine_changed:
                # Machine changed: create new production without marking old as completed
                insert_sql = """
                    INSERT INTO production (machine_id, article_id, quantity, start_date, end_date, hour_start, hour_end, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql,
                    (machine_id, old_article_id, quantity, start_date, end_date, hour_start, hour_end, status)
                )
                new_production_id = cursor.lastrowid

                # Move assignments to new machine/production for the current week
                week_number = datetime.strptime(start_date, '%Y-%m-%d').date().isocalendar()[1]
                year = datetime.strptime(start_date, '%Y-%m-%d').date().year

                copy_schedule_sql = """
                        INSERT INTO schedule (machine_id, production_id, operator_id, shift_id, position, week_number, year)
                    SELECT %s, %s, operator_id, shift_id, position, week_number, year
                    FROM schedule
                    WHERE machine_id = %s AND production_id = %s AND week_number = %s AND year = %s
                """
                cursor.execute(
                    copy_schedule_sql,
                    (machine_id, new_production_id, old_machine_id, production_id, week_number, year)
                )
                delete_old_sql = """
                    DELETE FROM schedule
                    WHERE machine_id = %s AND production_id = %s AND week_number = %s AND year = %s
                """
                cursor.execute(
                    delete_old_sql,
                    (old_machine_id, production_id, week_number, year)
                    )

                connection.commit()
                return jsonify({'success': True, 'message': 'Production split and new production created successfully (machine changed)'})
            else:
                # Only update the fields that changed (quantity, status, end_date)
                updates = []
                params = []

                if quantity is not None and str(quantity) != str(old_quantity):
                    updates.append("quantity = %s")
                    params.append(quantity)
                if status is not None and str(status) != str(old_status):
                    updates.append("status = %s")
                    params.append(status)
                if end_date is not None and (not old_end_date or str(end_date) != str(old_end_date)):
                    updates.append("end_date = %s")
                    params.append(end_date)
                elif end_date is None and old_end_date is not None:
                    updates.append("end_date = NULL")
                if hour_start is not None:
                    updates.append("hour_start = %s")
                    params.append(hour_start)
                else:
                    updates.append("hour_start = NULL")
                if hour_end is not None:
                    updates.append("hour_end = %s")
                    params.append(hour_end)
                else:
                    updates.append("hour_end = NULL")

                if not updates:
                    return jsonify({'success': True, 'message': 'No changes detected'})

                sql = f"UPDATE production SET {', '.join(updates)} WHERE id = %s"
                params.append(production_id)
                cursor.execute(sql, params)
                connection.commit()
                return jsonify({'success': True, 'message': 'Production updated successfully (no split)'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/rest_days')
@login_required
def rest_days():
    if not has_page_access('rest_days'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    # Get start_date from query or use today
    start_date_str = request.args.get('start_date')
    if start_date_str:
        week_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    else:
        # Find the Saturday of the current week for today
        today = datetime.now().date()
        week_start = today - timedelta(days=(today.weekday() - 5) % 7)  # 5 = Saturday
    week_end = week_start + timedelta(days=6)
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM operators WHERE status = 'active' ORDER BY name")
            operators = cursor.fetchall()
            # Get rest days for this week
            cursor.execute("SELECT * FROM operator_rest_days WHERE date BETWEEN %s AND %s", (week_start, week_end))
            rest_days = cursor.fetchall()
    finally:
        connection.close()
    # Map: (operator_id, date) -> True
    rest_map = {(r['operator_id'], str(r['date'])[:10]): True for r in rest_days}
    week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    current_access = get_user_accessible_pages(current_user.id)
    can_edit = current_access.get('rest_days', True) if current_user.role != 'admin' else True
    return render_template('rest_days.html', week_start=week_start, week_end=week_end, week_dates=week_dates, operators=operators, rest_map=rest_map, day_name=day_name, timedelta=timedelta, can_edit=can_edit)

@app.route('/api/rest_days', methods=['GET', 'POST'])
@login_required
def api_rest_days():
    if request.method == 'POST':
        if not has_page_access('rest_days', require_edit=True):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    if request.method == 'GET':
        week = int(request.args.get('week'))
        year = int(request.args.get('year'))
        # Use the correct week calculation (Saturday to Friday)
        week_start, week_end = get_week_start_end_saturday(year, week)
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM operator_rest_days WHERE date BETWEEN %s AND %s", (week_start, week_end))
                rest_days = cursor.fetchall()
        finally:
            connection.close()
        return jsonify(rest_days)
    else:
        data = request.get_json()
        start_date_str = data.get('start_date')
        rest_days = data['rest_days']  # List of {operator_id, date}
        if start_date_str:
            week_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            today = datetime.now().date()
            week_start = today - timedelta(days=(today.weekday() - 5) % 7)  # 5 = Saturday
        week_end = week_start + timedelta(days=6)
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Remove existing for this week
                cursor.execute("DELETE FROM operator_rest_days WHERE date BETWEEN %s AND %s", (week_start, week_end))
                # Group rest days by operator, deduplicate dates
                from collections import defaultdict
                op_days = defaultdict(set)
                for entry in rest_days:
                    operator_id = entry['operator_id']
                    rest_date = datetime.strptime(entry['date'], "%Y-%m-%d").date()
                    op_days[operator_id].add(rest_date)
                # For each operator, delete all 'Repos' absences for this week, then insert new grouped absences
                for operator_id, days in op_days.items():
                    # Remove all 'Repos' absences for this operator in this week
                    cursor.execute(
                        """
                        DELETE FROM absences
                        WHERE operator_id = %s
                        AND reason = 'Repos'
                        AND start_date >= %s AND end_date <= %s
                        """,
                        (operator_id, week_start, week_end)
                    )
                    days = sorted(days)
                    ranges = []
                    if days:
                        start = end = days[0]
                        for d in days[1:]:
                            if (d - end).days == 1:
                                end = d
                            else:
                                ranges.append((start, end))
                                start = end = d
                        ranges.append((start, end))
                    for start, end in ranges:
                        # Insert the new absence for the range
                        cursor.execute(
                            """
                            INSERT INTO absences (operator_id, start_date, end_date, reason, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            """,
                            (operator_id, start, end, 'Repos')
                        )
                    # Insert all rest_days as before, deduplicated
                    for d in days:
                        cursor.execute(
                            "INSERT INTO operator_rest_days (operator_id, date) VALUES (%s, %s)",
                            (operator_id, d)
                        )
            connection.commit()
        finally:
            connection.close()
        return jsonify({'success': True})

@app.route('/export_rest_days', methods=['GET'])
@login_required
def export_rest_days():
    start_date_str = request.args.get('start_date')
    lang = request.args.get('lang', 'fr')
    if start_date_str:
        week_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    else:
        today = datetime.now().date()
        week_start = today - timedelta(days=(today.weekday() - 5) % 7)  # 5 = Saturday
    week_end = week_start + timedelta(days=6)
    if lang == 'ar':
        font_paths = [
            '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
            '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
            'static/fonts/Amiri-Regular.ttf',
        ]
        bold_font_paths = [
            'static/fonts/Amiri-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        font_found = False
        for path in font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Arabic', path))
                arabic_font = 'Arabic'
                font_found = True
                break
        if not font_found:
            pdfmetrics.registerFont(TTFont('Arabic', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            arabic_font = 'Arabic'
        bold_font_found = False
        for path in bold_font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Arabic-Bold', path))
                arabic_bold_font = 'Arabic-Bold'
                bold_font_found = True
                break
        if not bold_font_found:
            arabic_bold_font = arabic_font
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        def process_arabic(text):
            if not text:
                return ""
            text = str(text)
            reshaped_text = reshape(text)
            return get_display(reshaped_text)
        header_text = process_arabic(f"أيام الراحة من {week_start.strftime('%Y/%m/%d')} إلى {week_end.strftime('%Y/%m/%d')}")
        jours_raw = ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']
        jours = [process_arabic(day) for day in jours_raw]
        jours = list(reversed(jours))  # Reverse for RTL
        weekday_to_label = dict(zip([5, 6, 0, 1, 2, 3, 4], list(reversed(jours))))
    else:
        arabic_font = 'Helvetica'
        arabic_bold_font = 'Helvetica-Bold'
        # French/Latin font registration for bold
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'static/fonts/Amiri-Regular.ttf'
        ]
        bold_font_paths = [
            'static/fonts/Amiri-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        font_found = False
        for path in font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Amiri', path))
                font_name = 'Amiri'
                font_found = True
                break
        if not font_found:
            font_name = 'Helvetica'
        bold_font_found = False
        for path in bold_font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Amiri-Bold', path))
                bold_font_name = 'Amiri-Bold'
                bold_font_found = True
                break
        if not bold_font_found:
            bold_font_name = 'Helvetica-Bold'
        jours = ['Samedi', 'Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        weekday_to_label = dict(zip([5, 6, 0, 1, 2, 3, 4], jours))
        header_text = f"Repos De {week_start.strftime('%d/%m/%Y')} à {week_end.strftime('%d/%m/%Y')}"
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM operators WHERE status = 'active' ORDER BY name")
            operators = cursor.fetchall()
            cursor.execute("SELECT * FROM operator_rest_days WHERE date BETWEEN %s AND %s", (week_start, week_end))
            rest_days = cursor.fetchall()
    finally:
        connection.close()
    # Step 1: Update the rest_map to collect all rest dates per operator
    from collections import defaultdict
    rest_map = defaultdict(list)
    for r in rest_days:
        rest_map[r['operator_id']].append(r['date'])
    # Step 2: Update the day_to_ops population to loop through each rest date per operator
    day_to_ops = {label: [] for label in jours}
    for op in operators:
        rest_dates = rest_map.get(op['id'], [])
        for rest_date in rest_dates:
            rest_date_obj = rest_date if isinstance(rest_date, date) else datetime.strptime(str(rest_date), '%Y-%m-%d').date()
            day_label = weekday_to_label.get(rest_date_obj.weekday())
            if day_label:
                if lang == 'ar' and op.get('arabic_name'):
                    from arabic_reshaper import reshape
                    from bidi.algorithm import get_display
                    name = get_display(reshape(op['arabic_name']))
                else:
                    name = op['name'].capitalize()
                day_to_ops[day_label].append(name)
    # For each day, determine how many columns are needed (26 per column)
    day_col_counts = {}
    for day in jours:
        count = len(day_to_ops[day])
        day_col_counts[day] = (count // 26) + (1 if count % 26 else 0)
    # Build the table header dynamically
    table_header = []
    day_col_map = []  # List of (day_label, col_index_within_day)
    for day in jours:
        for i in range(day_col_counts[day]):
            table_header.append(day)
            day_col_map.append((day, i))
    col_count = len(table_header)
    # Build rows: always 26 rows (since each column for a day can have up to 26 ops)
    max_rows = 26
    rows = []
    for row_idx in range(max_rows):
        row = [''] * col_count
        col_ptr = 0
        for day in jours:
            ops = day_to_ops[day]
            for col_in_day in range(day_col_counts[day]):
                op_idx = row_idx + col_in_day * 26
                if op_idx < len(ops):
                    row[col_ptr] = ops[op_idx]
                col_ptr += 1
        rows.append(row)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    # Add header as Paragraph with red color and correct font
    from reportlab.lib.styles import ParagraphStyle
    header_style = ParagraphStyle(
        name='Header',
        parent=styles['Title'],
        textColor='red',
        fontName=arabic_font,
        fontSize=18,
        alignment=1
    )
    header = Paragraph(header_text, header_style)
    elements.append(header)
    elements.append(Spacer(1, 12))
    data = [table_header] + rows
    t = Table(data, colWidths=[max(100, 700//col_count)]*col_count)
    # Set the correct bold font variable for the header row
    if lang == 'ar':
        header_bold_font = arabic_bold_font
    else:
        header_bold_font = bold_font_name
    table_style = [
        ('BACKGROUND', (0,0), (-1,0), '#e3e6ed'),
        ('TEXTCOLOR', (0,0), (-1,0), '#222'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), header_bold_font),
        ('FONTSIZE', (0,0), (-1,0), header_font_size if 'header_font_size' in locals() else 14),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 1, 'black'),
        ('FONTNAME', (0,1), (-1,-1), arabic_bold_font),
        ('ROWHEIGHT', (0,0), (-1,-1), 18),
    ]
    if lang == 'ar' or lang == 'fr':
        # Set per-cell font size for all names
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, cell in enumerate(row):
                if cell and isinstance(cell, str):
                    word_count = len(cell.split())
                    if lang == 'fr':
                        font_size = 8 if len(cell) > 20 else 9 if (len(cell) == 20 or len(cell) == 19) else 10
                    else:
                        font_size = 10 if word_count >= 4 else 11 if word_count == 3 else 12
                    table_style.append(('FONTSIZE', (col_idx, row_idx), (col_idx, row_idx), font_size))
                    table_style.append(('VALIGN', (col_idx, row_idx), (col_idx, row_idx), 'TOP'))
                    table_style.append(('TOPPADDING', (col_idx, row_idx), (col_idx, row_idx), 1))
                    table_style.append(('BOTTOMPADDING', (col_idx, row_idx), (col_idx, row_idx), 5))
    # Remove the else branch for static FONTSIZE
    t.setStyle(TableStyle(table_style))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"rest_days_{week_start.strftime('%d-%m-%Y')}_to_{week_end.strftime('%d-%m-%Y')}_{lang}.pdf", mimetype='application/pdf')

def get_week_start_end_saturday(year, week):
    # Find the first Saturday of the year
    jan1 = datetime(year, 1, 1)
    days_to_saturday = (5 - jan1.weekday()) % 7  # 5 = Saturday
    first_saturday = jan1 + timedelta(days=days_to_saturday)
    # Calculate the start of the requested week
    week_start = first_saturday + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

# Register Noto Naskh Arabic fonts using robust path resolution
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts')
NASKH_REGULAR_PATH = os.path.join(FONTS_DIR, 'NotoNaskhArabic-Regular.ttf')
NASKH_BOLD_PATH = os.path.join(FONTS_DIR, 'NotoNaskhArabic-Bold.ttf')
NASKH_VARIABLE_PATH = os.path.join(FONTS_DIR, 'NotoNaskhArabic-VariableFont_wght.ttf')
AMIRI_REGULAR_PATH = os.path.join(FONTS_DIR, 'Amiri-Regular.ttf')
AMIRI_BOLD_PATH = os.path.join(FONTS_DIR, 'Amiri-Bold.ttf')

# Default to NotoNaskhArabic
arabic_font = 'NotoNaskhArabic'
arabic_bold_font = 'NotoNaskhArabic-Bold'

# Try Amiri first
try:
    pdfmetrics.registerFont(TTFont('Amiri', AMIRI_REGULAR_PATH))
    arabic_font = 'Amiri'
except Exception as e:
    print(f"Font load failed for Amiri: {e}")

try:
    pdfmetrics.registerFont(TTFont('Amiri-Bold', AMIRI_BOLD_PATH))
    arabic_bold_font = 'Amiri-Bold'
except Exception as e:
    print(f"Font load failed for Amiri-Bold: {e}")

# If Amiri is not available, try NotoNaskhArabic
if arabic_font != 'Amiri':
    try:
        if os.path.exists(NASKH_REGULAR_PATH):
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic', NASKH_REGULAR_PATH))
        else:
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic', NASKH_VARIABLE_PATH))
    except Exception as e:
        print(f"Font load failed for NotoNaskhArabic: {e}")
        arabic_font = 'Amiri'  # fallback to Amiri

if arabic_bold_font != 'Amiri-Bold':
    try:
        if os.path.exists(NASKH_BOLD_PATH):
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic-Bold', NASKH_BOLD_PATH))
        else:
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic-Bold', NASKH_VARIABLE_PATH))
    except Exception as e:
        print(f"Font load failed for NotoNaskhArabic-Bold: {e}")
        arabic_bold_font = 'Amiri-Bold'  # fallback to Amiri-Bold

# Register Amiri font with absolute path
pdfmetrics.registerFont(TTFont('Amiri', 'static/fonts/Amiri-Regular.ttf'))

# Register Amiri font for all PDF output
FONT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'fonts', 'Amiri-Regular.ttf')
pdfmetrics.registerFont(TTFont('Amiri', FONT_PATH))

# In all PDF export functions, set:
font_name = 'Amiri'
bold_font_name = 'Amiri'
# Use font_name and bold_font_name in all TableStyle, ParagraphStyle, and canvas.setFont calls for all output.
# Remove any logic that sets Arial or other fonts as the default for non-Arabic output.

@app.route('/debug_history')
@login_required
def debug_history():
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    history_data = get_daily_schedule_history(start_date, end_date)
    
    debug_output = []
    debug_output.append(f"<h2>History Debug</h2>")
    debug_output.append(f"<p>Date range: {start_date} to {end_date}</p>")
    debug_output.append(f"<p>Total dates: {len(history_data)}</p>")
    debug_output.append("<hr>")
    
    for date_key, machines in history_data.items():
        debug_output.append(f"<h3>Date: {date_key}</h3>")
        debug_output.append(f"<p>Total machines: {len(machines)}</p>")
        
        machine_list = list(machines.keys())
        debug_output.append(f"<p>Machines: {', '.join(machine_list[:30])}</p>")
        
        if 'EMBALLAGES' in machines:
            debug_output.append(f"<p style='color:green;font-weight:bold;'>✅ EMBALLAGES FOUND with {len(machines['EMBALLAGES'])} assignments</p>")
            debug_output.append(f"<pre>{machines['EMBALLAGES']}</pre>")
        else:
            debug_output.append(f"<p style='color:red;font-weight:bold;'>❌ EMBALLAGES NOT FOUND</p>")
        debug_output.append("<hr>")
    
    return '\n'.join(debug_output)

if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"Server is starting on http://{local_ip}:8000 ...")
    serve(app, host="0.0.0.0", port=8000)
