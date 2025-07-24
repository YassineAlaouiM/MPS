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
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor  # <-- Use DictCursor directly
}

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
# login_manager.login_view = 'login'  # <-- Remove or comment out this line

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
    return pymysql.connect(**db_config)

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

#Non-Functioning Machines Management (Mahcines en panne)
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
            cursor.execute(sql, (machine_id, issue, reported_date))
            connection.commit()
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
            # Get machine_id
            sql = "SELECT machine_id FROM non_functioning_machines WHERE id = %s"
            cursor.execute(sql, (id,))
            result = cursor.fetchone()
            if not result or not isinstance(result, dict):
                return jsonify({'success': False, 'message': 'Record not found'})

            machine_id = result['machine_id']

            # Update non_functioning_machines with fixed date
            sql = "UPDATE non_functioning_machines SET fixed_date = %s WHERE id = %s"
            cursor.execute(sql, (fixed_date, id))

            # Update machine status to operational
            sql = "UPDATE machines SET status = 'operational' WHERE id = %s"
            cursor.execute(sql, (machine_id,))

            connection.commit()
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
    
    print(f"Creating production with data: {data}")  # Debug log
    
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
                INSERT INTO production (machine_id, article_id, quantity, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
            """
            cursor.execute(sql, (machine_id, article_id, quantity, start_date, end_date))
                
            connection.commit()
            print("Production record created successfully")  # Debug log
            return jsonify({'success': True, 'message': 'Production added successfully'})
    except pymysql.Error as e:
        print(f"Database error: {str(e)}")  # Debug log
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
        with connection.cursor() as cursor:
            sql = """
                SELECT p.*, m.name as machine_name, m.type as machine_type, a.name as article_name
                FROM production p
                JOIN machines m ON p.machine_id = m.id
                LEFT JOIN articles a ON p.article_id = a.id
                WHERE p.id = %s
            """
            cursor.execute(sql, (id,))
            production = cursor.fetchone()
            
            if production and isinstance(production, dict):
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
                    'status': production['status']
                })
            else:
                return jsonify({'success': False, 'message': 'Production record not found'}), 404
    except pymysql.Error as e:
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
                    JOIN articles a ON p.article_id = a.id
                    WHERE p.status = 'active'
                    AND CURDATE() BETWEEN p.start_date AND COALESCE(p.end_date, CURDATE())
                """)
                return cursor.fetchall()
    except Exception as e:
        flash(f"Error loading machines in production: {str(e)}", "error")
        return []

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
                    WHERE o.status != 'inactive'
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
                    SELECT m.*, p.id as production_id, p.article_id, a.name as article_name
                    FROM machines m
                    JOIN production p ON m.id = p.machine_id
                    LEFT JOIN articles a ON p.article_id = a.id
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
                operators = get_operators(week, year)
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
                         shifts=shifts,
                         assignments=assignments,
                         can_edit=can_edit,
                         articles=articles)  # Pass articles and all_machines for modal

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
            # Clear existing assignments for this week
            cursor.execute("""
                DELETE FROM schedule 
                WHERE week_number = %s AND year = %s
            """, (week_number, year))
            
            # Save new assignments to the database
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

#PDF
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
                font_name = arabic_font
                bold_font_name = arabic_bold_font
            else:
                font_name = 'Arial'
                bold_font_name = 'Arial-Bold'
            font_paths = [
                '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
                '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
                'C:\\Windows\\Fonts\\arial.ttf'
            ]
            bold_font_paths = [
                'C:\\Windows\\Fonts\\arialbd.ttf',
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
            canvas.setFont(font_name, 20)
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
                            processed_operators.append(operator)
                        text = '\n+ '.join(processed_operators)
                    else:
                        # Single operator case - original behavior
                        words = text.split()
                        processed_words = []
                        for i in range(0, len(words), 2):
                            if i + 1 < len(words):
                                processed_words.append(words[i] + ' ' + words[i + 1])
                            else:
                                processed_words.append(words[i])
                        text = '\n'.join(processed_words)
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
                        processed_operators.append(operator.capitalize())
                    return '\n+ '.join(processed_operators)
                else:
                    # Single operator case - original behavior
                    words = text.split()
                    words = [word.strip().capitalize() for word in words]
                    if len(words) > 2:
                        processed_words = []
                        for i in range(0, len(words), 2):
                            if i + 1 < len(words):
                                processed_words.append(words[i] + ' ' + words[i + 1])
                            else:
                                processed_words.append(words[i])
                        return '\n'.join(processed_words)
                    return ' '.join(words)
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
            # Create table
            table = Table(
                table_data,
                colWidths=[col_width] * num_columns,
                rowHeights=[row_height] * len(table_data)
            )
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), table_header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), bold_font_name),  # Table header row bold
                ('FONTNAME', (0, 1), (0, -1), bold_font_name),  # First column (machines) bold
                ('FONTNAME', (1, 1), (-1, -1), font_name),      # Other cells normal
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 0),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
                ('FONTSIZE', (0, 1), (0, -1), 12),
                ('FONTSTYLE', (0, 1), (0, -1), 'UPPERCASE'),
                ('FONTSIZE', (1, 1), (-1, -1), 10 if name_type == 'latin' else 15),
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
            return (len(table_data) * row_height) + 30  # 30px gap after table

        # --- END: Separate tables for model shift 1 and model shift 2 ---

        def add_page_footer(canvas, page_num, total_pages):
            # Add current date and time at the bottom center
            now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            canvas.setFont(font_name, 10)
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.drawCentredString(page_width / 2, 20, now)

        # Generate the page(s)
        p.setFont(font_name, 20)
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

# Add this after the User class definition
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

# Add this decorator function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Add these routes after the existing routes
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
            
            assignments = cursor.fetchall()
            
            # Insert each assignment into daily history
            for assignment in assignments:
                cursor.execute('''
                    INSERT INTO daily_schedule_history (
                        date_recorded, week_number, year,
                        machine_id, production_id, operator_id, shift_id, position,
                        machine_name, operator_name, shift_name, shift_start_time, shift_end_time,
                        article_name, article_abbreviation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    date_to_save, assignment['week_number'], assignment['year'],
                    assignment['machine_id'], assignment['production_id'], 
                    assignment['operator_id'], assignment['shift_id'], assignment['position'],
                    assignment['machine_name'], assignment['operator_name'], 
                    assignment['shift_name'], assignment['start_time'], assignment['end_time'],
                    assignment['article_name'], assignment['article_abbreviation']
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
                
                # Get all assignments for this date
                cursor.execute('''
                    SELECT 
                        machine_name, operator_name, shift_name, 
                        shift_start_time, shift_end_time, article_name, article_abbreviation
                    FROM daily_schedule_history
                    WHERE date_recorded = %s
                    ORDER BY machine_name, shift_start_time, position
                ''', (date_recorded,))
                
                assignments = cursor.fetchall()
                
                # Structure: {machine: [{operator, shift, start_time, end_time, article}]}
                day_data = {}
                for assignment in assignments:
                    machine = assignment['machine_name']
                    if machine not in day_data:
                        day_data[machine] = []
                    
                    article_info = ""
                    if assignment['article_name']:
                        article_info = assignment['article_abbreviation'] or assignment['article_name']
                    
                    day_data[machine].append({
                        'operator': assignment['operator_name'],
                        'shift': assignment['shift_name'],
                        'start_time': str(assignment['shift_start_time']),
                        'end_time': str(assignment['shift_end_time']),
                        'article': article_info
                    })
                
                # Use date as key (YYYY-MM-DD format)
                key = date_recorded.strftime('%Y-%m-%d')
                history[key] = day_data
            
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
                    # Copy all records from last_date to today
                    cursor.execute("SELECT * FROM daily_schedule_history WHERE date_recorded = %s", (last_date,))
                    rows = cursor.fetchall()
                    for row in rows:
                        # Remove the id and change date_recorded to today
                        row_data = dict(row)
                        row_data['date_recorded'] = today
                        row_data.pop('id', None)
                        columns = ', '.join(row_data.keys())
                        placeholders = ', '.join(['%s'] * len(row_data))
                        cursor.execute(f"INSERT INTO daily_schedule_history ({columns}) VALUES ({placeholders})", tuple(row_data.values()))
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
    name_type = request.args.get('name_type', 'latin')  # Default to latin names

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
            # Handles time strings like '07:00:00' or '7:00:00'
            def extract_hour(t):
                t_str = str(t)
                if ':' in t_str:
                    hour_part = t_str.split(':')[0]
                    try:
                        return f"{int(hour_part)}h"
                    except Exception:
                        return t_str  # fallback to raw string if conversion fails
                try:
                    return f"{int(t_str)}h"
                except Exception:
                    return t_str
            start_h = extract_hour(start)
            end_h = extract_hour(end)
            return f"{start_h} à {end_h}"
        shift_headers = {f'shift_{s["id"]}': format_shift_time(s['start_time'], s['end_time']) for s in shifts}
        shift_keys = [f'shift_{s["id"]}' for s in shifts]

        # Get all assignments for the day
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
                WHERE d.date_recorded = %s
                ORDER BY d.machine_name, d.shift_id
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
                WHERE d.date_recorded = %s
                ORDER BY d.machine_name, d.shift_id
            ''', (date_obj,))
        assignments = cursor.fetchall()
        conn.close()

        # Build data structure: {machine: {shift_key: operator_name, ...}, ...}
        machine_data = {}
        machine_articles = {}
        machine_types = {}
        for row in assignments:
            m = row['machine_name']
            s = shift_id_to_key[row['shift_id']]
            op = row['operator_name']
            article = row['article_name']
            abbr = row['article_abbreviation']
            mtype = row.get('machine_type', 0)
            if m not in machine_data:
                machine_data[m] = {}
                machine_articles[m] = (article, abbr)
                machine_types[m] = mtype
            machine_data[m][s] = op

        # Prepare rows for the PDF (like export_sch)
        model1_shift_keys = ['shift_1', 'shift_2', 'shift_3']
        model2_shift_keys = ['shift_4', 'shift_5']
        model3_shift_keys = ['shift_6']
        model1_rows = []
        model2_rows = []
        model3_rows = []
        for m in sorted(machine_data.keys()):
            row_dict = {
                'machine_name': m,
                'machine_type': machine_types[m],
                'article_name': machine_articles[m][0],
                'article_abbreviation': machine_articles[m][1],
            }
            for k in shift_keys:
                row_dict[k] = machine_data[m].get(k, '')
            # Assign to model
            if any(row_dict[k] for k in model1_shift_keys):
                model1_rows.append(row_dict)
            elif any(row_dict[k] for k in model2_shift_keys):
                model2_rows.append(row_dict)
            elif any(row_dict[k] for k in model3_shift_keys):
                model3_rows.append(row_dict)

        # PDF generation (same as export_sch)
        buffer = BytesIO()
        page_width, page_height = portrait(A4)
        p = canvas.Canvas(buffer, pagesize=portrait(A4))

        try:
            if name_type == 'arabic' or (lang if 'lang' in locals() else None) == 'ar':
                font_name = arabic_font
                bold_font_name = arabic_bold_font
            else:
                font_name = 'Arial'
                bold_font_name = 'Arial-Bold'
            font_paths = [
                '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
                '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
                'C:\\Windows\\Fonts\\arial.ttf'
            ]
            bold_font_paths = [
                'C:\\Windows\\Fonts\\arialbd.ttf',
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
            canvas.setFont(font_name, 20)
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
                            processed_operators.append(operator)
                        text = '\n+ '.join(processed_operators)
                    else:
                        words = text.split()
                        processed_words = []
                        for i in range(0, len(words), 2):
                            if i + 1 < len(words):
                                processed_words.append(words[i] + ' ' + words[i + 1])
                            else:
                                processed_words.append(words[i])
                        text = '\n'.join(processed_words)
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
                        processed_operators.append(operator.capitalize())
                    return '\n+ '.join(processed_operators)
                else:
                    words = text.split()
                    words = [word.strip().capitalize() for word in words]
                    if len(words) > 2:
                        processed_words = []
                        for i in range(0, len(words), 2):
                            if i + 1 < len(words):
                                processed_words.append(words[i] + ' ' + words[i + 1])
                            else:
                                processed_words.append(words[i])
                        return '\n'.join(processed_words)
                    return ' '.join(words)
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
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0a8231')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), bold_font_name),
                ('FONTNAME', (0, 1), (0, -1), bold_font_name),
                ('FONTNAME', (1, 1), (-1, -1), font_name),
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
            canvas.setFont(font_name, 10)
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.drawCentredString(page_width / 2, 20, now)

        p.setFont(font_name, 20)
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

            # 2. Set the end_date of the current production to yesterday and mark as completed
            today = datetime.strptime(start_date, '%Y-%m-%d').date()
            yesterday = today - timedelta(days=1)
            cursor.execute(
                "UPDATE production SET end_date = %s, status = 'completed' WHERE id = %s",
                (yesterday.strftime('%Y-%m-%d'), production_id)
            )

            # 3. Insert the new production starting today
            insert_sql = """
                INSERT INTO production (machine_id, article_id, quantity, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                insert_sql,
                (machine_id, article_id, quantity, start_date, end_date, status)
            )
            new_production_id = cursor.lastrowid

            # 4. Update schedule assignments for the current week to point to the new production
            week_number = today.isocalendar()[1]
            year = today.year
            
            update_schedule_sql = """
                UPDATE schedule
                SET machine_id = %s, production_id = %s
                WHERE machine_id = %s AND production_id = %s AND week_number = %s AND year = %s
            """
            cursor.execute(
                update_schedule_sql,
                (machine_id, new_production_id, old_machine_id, production_id, week_number, year)
            )

            connection.commit()
            return jsonify({'success': True, 'message': 'Production split and new production created successfully'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

@app.route('/rest_days')
@login_required
def rest_days():
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
    return render_template('rest_days.html', week_start=week_start, week_end=week_end, week_dates=week_dates, operators=operators, rest_map=rest_map, day_name=day_name, timedelta=timedelta)

@app.route('/api/rest_days', methods=['GET', 'POST'])
@login_required
def api_rest_days():
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
            'C:\\Windows\\Fonts\\arial.ttf',
        ]
        bold_font_paths = [
            'C:\\Windows\\Fonts\\arialbd.ttf',
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
            'C:\\Windows\\Fonts\\arial.ttf'
        ]
        bold_font_paths = [
            'C:\\Windows\\Fonts\\arialbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        font_found = False
        for path in font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Arial', path))
                font_name = 'Arial'
                font_found = True
                break
        if not font_found:
            font_name = 'Helvetica'
        bold_font_found = False
        for path in bold_font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('Arial-Bold', path))
                bold_font_name = 'Arial-Bold'
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
        ('FONTSIZE', (0,0), (-1,0), header_font_size if 'header_font_size' in locals() else 13),
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
                        font_size = 8 if word_count >= 4 else 9 if word_count == 3 else 10
                    table_style.append(('FONTSIZE', (col_idx, row_idx), (col_idx, row_idx), font_size))
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
        arabic_font = 'Arial'  # fallback to Arial

if arabic_bold_font != 'Amiri-Bold':
    try:
        if os.path.exists(NASKH_BOLD_PATH):
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic-Bold', NASKH_BOLD_PATH))
        else:
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic-Bold', NASKH_VARIABLE_PATH))
    except Exception as e:
        print(f"Font load failed for NotoNaskhArabic-Bold: {e}")
        arabic_bold_font = 'Arial-Bold'  # fallback to Arial-Bold

# Register Amiri font with absolute path
pdfmetrics.registerFont(TTFont('Amiri', '/home/ubuntu/MPS/static/fonts/Amiri-Regular.ttf'))

if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"Server is starting on http://{local_ip}:8000 ...")
    serve(app, host="0.0.0.0", port=8000)
