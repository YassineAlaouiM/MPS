from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
from waitress import serve
import socket
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'schedule_management'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
            if user:
                return User(user['id'], user['username'], user['role'])
    finally:
        connection.close()
    return None

def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def dashboard():
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
                
                if user and check_password_hash(user['password'], password):
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

@app.route('/machines')
@login_required
def machines():
    if not has_page_access('machines'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM machines ORDER BY status"
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
    finally:
        connection.close()
    return render_template('machines.html', machines=machines, non_functioning_machines=non_functioning_machines)

@app.route('/operators')
@login_required
def operators():
    if not has_page_access('operators'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM operators ORDER BY (status='active') DESC, (status='absent') DESC, (status='inactive') DESC"
            cursor.execute(sql)
            operators = cursor.fetchall()
            sql = '''
                SELECT a.*, o.name as operator_name
                FROM absences a
                JOIN operators o ON a.operator_id = o.id
                ORDER BY a.end_date DESC
            '''
            cursor.execute(sql)
            absences = cursor.fetchall()
    finally:
        connection.close()
    return render_template('operators.html', operators=operators, absences=absences)

@app.route('/production')
@login_required
def production():
    if not has_page_access('production'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get all articles
            sql = "SELECT * FROM articles ORDER BY name"
            cursor.execute(sql)
            articles = cursor.fetchall()
            
            # Get all operational machines
            sql = "SELECT * FROM machines WHERE status = 'operational' ORDER BY name"
            cursor.execute(sql)
            machines = cursor.fetchall()
            
            # Get all production records with machine and article details
            sql = '''
                SELECT p.*, m.name as machine_name, m.type as machine_type, a.name as article_name
                FROM production p
                JOIN machines m ON p.machine_id = m.id
                LEFT JOIN articles a ON p.article_id = a.id
                ORDER BY p.status, p.start_date DESC
            '''
            cursor.execute(sql)
            production = cursor.fetchall()
    finally:
        connection.close()
    return render_template('production.html', articles=articles, machines=machines, production=production)

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
    machine_type = data.get('type', False)  #Default is False (Machine), True (Service)
    
    if not name:
        return jsonify({'success': False, 'message': 'Machine name is required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO machines (name, status, type) VALUES (%s, %s, %s)"
            cursor.execute(sql, (name, status, machine_type))
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
            sql = "SELECT * FROM machines WHERE id = %s AND status = 'operational'"
            cursor.execute(sql, (machine_id,))
            machine = cursor.fetchone()
            if machine:
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
    machine_type = data.get('type')

    if not name or not status:
        return jsonify({'success': False, 'message': 'Name and status are required'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE machines SET name = %s, status = %s, type = %s WHERE id = %s"
            cursor.execute(sql, (name, status, machine_type, machine_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Machine updated successfully'})
    except Exception as e:
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

#Operator Management
@app.route('/api/operators', methods=['POST'])
@login_required
def create_operator():
    data = request.get_json()
    name = data.get('name')
    arabic_name = data.get('arabic_name')
    status = data.get('status', 'active')

    if not name or not arabic_name:
        return jsonify({'success': False, 'message': 'Name and Arabic name are required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert new operator without requiring operator_id
            sql = "INSERT INTO operators (name, arabic_name, status) VALUES (%s, %s, %s)"
            cursor.execute(sql, (name, arabic_name, status))
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
            sql = "SELECT id, name, arabic_name, status FROM operators WHERE id = %s"
            cursor.execute(sql, (operator_id,))
            operator = cursor.fetchone()
            if operator:
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
    status = data.get('status')

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

            # Update operator details with required Arabic name
            sql = "UPDATE operators SET name = %s, arabic_name = %s, status = %s WHERE id = %s"
            cursor.execute(sql, (name, arabic_name, status, operator_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Operator updated successfully'})
    except pymysql.Error as e:
        return jsonify({'success': False, 'message': str(e)})
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
            if not result:
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
            if not absence:
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
            
            if not current_absence:
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
            if not result:
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
    description = data.get('description')
    
    if not name:
        return jsonify({'success': False, 'message': 'Article name is required'})
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO articles (name, description) VALUES (%s, %s)"
            cursor.execute(sql, (name, description))
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
    description = data.get('description')

    if not name:
        return jsonify({'success': False, 'message': 'Article name is required'})

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE articles SET name = %s, description = %s WHERE id = %s"
            cursor.execute(sql, (name, description, article_id))
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
            if machine_result and machine_result['type']:
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
            
            if production:
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
    except Exception as e:
        flash(f"Error loading shifts: {str(e)}", "error")
        shifts = []
    
    return render_template('shifts.html', shifts=shifts)

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
    if not has_page_access('schedule'):
        flash('Access denied')
        return redirect(url_for('dashboard'))
    week = request.args.get('week', default=datetime.now().isocalendar()[1], type=int)
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    # Get machines that were in production during the selected week
    machines = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get the start and end dates of the selected week
                cursor.execute("""
                    SELECT 
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Monday'), '%%Y %%u %%W') as week_start,
                        STR_TO_DATE(CONCAT(%s, ' ', %s, ' Sunday'), '%%Y %%u %%W') as week_end
                """, (year, week, year, week))
                week_dates = cursor.fetchone()
                
                if not week_dates or not week_dates['week_start'] or not week_dates['week_end']:
                    flash(f"Error calculating week dates for week {week} of {year}", "error")
                    return render_template('schedule.html', machines=[], operators=[], shifts=[], assignments=[])
                
                # Get machines and their production records that were active during this week
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
                
                # Get operators and shifts
                operators = get_operators(week, year)
                shifts = get_shifts()
                
                # Get current assignments for the selected week
                cursor.execute("""
                    SELECT s.id, s.machine_id, s.production_id, s.operator_id, s.shift_id, s.week_number, s.year,
                           m.name as machine_name, o.name as operator_name, sh.name as shift_name,
                           p.article_id, a.name as article_name
                    FROM schedule s
                    JOIN machines m ON s.machine_id = m.id
                    JOIN production p ON s.production_id = p.id
                    LEFT JOIN articles a ON p.article_id = a.id
                    JOIN operators o ON s.operator_id = o.id
                    JOIN shifts sh ON s.shift_id = sh.id
                    WHERE s.week_number = %s AND s.year = %s
                    ORDER BY m.name, p.start_date, sh.id
                """, (week, year))
                assignments = cursor.fetchall()
                
    except Exception as e:
        flash(f"Error loading machines: {str(e)}", "error")
        return render_template('schedule.html', machines=[], operators=[], shifts=[], assignments=[])
    
    return render_template('schedule.html', 
                         week=week,
                         year=year,
                         machines=machines,
                         operators=operators,
                         shifts=shifts,
                         assignments=assignments)

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
            # Validate that no operator is assigned to multiple shifts
            operator_assignments = set()
            for assignment in assignments:
                operator_id = assignment['operator_id']
                if operator_id in operator_assignments:
                    return jsonify({'success': False, 'message': f'Operateur {operator_id} est affecté à plusieurs shifts.'}), 400
                operator_assignments.add(operator_id)

            # Define shift models
            # Adding shifts is static
            shift_model_1 = {"1", "2", "3"}
            shift_model_2 = {"4", "5"}
            shift_model_3 = {"6"}

            # Validate that each machine+production combination is assigned to only one shift model per week
            machine_shift_models = {}
            for assignment in assignments:
                machine_id = assignment['machine_id']
                production_id = assignment['production_id']
                shift_id = assignment['shift_id']
                key = f"{machine_id}_{production_id}"

                # Determine the shift model for the current shift
                if shift_id in shift_model_1:
                    current_model = "model_1"
                elif shift_id in shift_model_2:
                    current_model = "model_2"
                elif shift_id in shift_model_3:
                    current_model = "model_3"
                else:
                    return jsonify({'success': False, 'message': f'Invalid shift ID {shift_id}.'}), 400

                # Check if the machine+production is already assigned to a different shift model
                if key in machine_shift_models:
                    if machine_shift_models[key] != current_model:
                        return jsonify({'success': False, 'message': f'Machine {machine_id} with production {production_id} is assigned to multiple shift models in the same week.'}), 400
                else:
                    machine_shift_models[key] = current_model

            # Validate that each machine+production has the exact number of operators for the shift model
            for key, model in machine_shift_models.items():
                machine_id, production_id = key.split('_')
                assigned_operators = [a for a in assignments if a['machine_id'] == machine_id and a['production_id'] == production_id]

                if model == "model_1" and len(assigned_operators) != 3:
                    return jsonify({'success': False, 'message': f'Machine {machine_id} with production {production_id} must have exactly 3 operators for shift model 1.'}), 400

                if model == "model_2" and len(assigned_operators) != 2:
                    return jsonify({'success': False, 'message': f'Machine {machine_id} with production {production_id} must have exactly 2 operators for shift model 2.'}), 400

                if model == "model_3" and len(assigned_operators) != 1:
                    return jsonify({'success': False, 'message': f'Machine {machine_id} with production {production_id} must have exactly 1 operator for shift model 3.'}), 400
	        # Clear existing assignments for this week
            cursor.execute("""
                DELETE FROM schedule 
                WHERE week_number = %s AND year = %s
            """, (week_number, year))
            
            #Save new assignments to the database
            for assignment in assignments:
                cursor.execute("""
                    INSERT INTO schedule (machine_id, production_id, operator_id, shift_id, week_number, year)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (assignment['machine_id'], assignment['production_id'], assignment['operator_id'], 
                      assignment['shift_id'], week_number, year))

            connection.commit()
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
                        SELECT m.id, m.name, p.id as production_id, p.article_id, a.name as article_name
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
                        SELECT m.id, m.name, p.id as production_id, p.article_id, a.name as article_name
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

                for machine in machines:
                    for shift in shifts:
                        if not available_operators:
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

                        selected_operator = None
                        for operator in available_operators:
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
                            selected_operator = available_operators[0]

                        available_operators.remove(selected_operator)

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
def export_schedule():
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
                p.id as production_id,
                a.name as article_name,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 1 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_1,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 2 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_2,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 3 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_3,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 4 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_4,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 5 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_5,
                GROUP_CONCAT(
                    CASE s.id
                        WHEN 6 THEN {name_field}
                        ELSE NULL
                    END
                ) AS shift_6
            FROM machines m
            INNER JOIN schedule sc ON m.id = sc.machine_id AND sc.week_number = %s AND sc.year = %s
            INNER JOIN production p ON sc.production_id = p.id
            LEFT JOIN articles a ON p.article_id = a.id
            LEFT JOIN shifts s ON sc.shift_id = s.id
            LEFT JOIN operators o ON sc.operator_id = o.id
            GROUP BY m.id, m.name, p.id, a.name
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
        page_width, page_height = landscape(A4)
        p = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        # Register appropriate font based on name type
        try:
            if name_type == 'arabic':
                font_paths = [
                    '/usr/share/fonts/truetype/kacst/KacstOne.ttf',
                    '/usr/share/fonts/truetype/arabeyes/ae_Arab.ttf',
                    'C:\\Windows\\Fonts\\arial.ttf'
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
            else:
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    'C:\\Windows\\Fonts\\arial.ttf'
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
        except Exception as e:
            print(f"Font registration error: {str(e)}")
            font_name = 'Helvetica'

        def process_text(text, is_header=False, is_machine=False):
            if not text:
                return ""
            text = str(text)
            if name_type == 'arabic' and any(ord(char) in range(0x0600, 0x06FF) for char in text):
                # For Arabic text, add line break after every two words
                if not is_header and not is_machine:
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
                # For Latin text in cells (not headers), add spaces and capitalize each word
                words = text.split()
                # Capitalize first letter of each word, rest lowercase
                words = [word.strip().capitalize() for word in words]
                return ' '.join(words)
            return text
        
        # Set colors
        header_color = colors.HexColor('#26438c')  # Blue
        table_header_color = colors.HexColor('#23335b')  # Lighter Blue
        row_color = colors.HexColor('#ecf0f1')  # Light Gray
        text_color = colors.HexColor('#23335b')  # Dark Blue

        def add_page_header(canvas, page_num, total_pages):
            # Add title
            canvas.setFont(font_name, 16)
            canvas.setFillColor(header_color)
            title_text = "جدول المناوبة" if name_type == 'arabic' else "Planning"
            canvas.drawCentredString(page_width/2, page_height - 40, process_text(title_text))
            
            # Add Week dates 
            def get_week_dates(year, week):
                jan_fourth = datetime(year, 1, 4)
                monday_week1 = jan_fourth - timedelta(days=jan_fourth.isocalendar()[2] - 1)
                target_monday = monday_week1 + timedelta(weeks=week-1)
                target_sunday = target_monday + timedelta(days=6)
                return target_monday, target_sunday

            week_start, week_end = get_week_dates(year, week)
            if name_type == 'arabic':
                week_dates = f"{week_start.strftime('%d/%m/%Y')} -> {week_end.strftime('%d/%m/%Y')}"
            else:
                week_dates = f"De {week_start.strftime('%d/%m/%Y')} à {week_end.strftime('%d/%m/%Y')}"
            
            canvas.setFont(font_name, 10)
            canvas.setFillColor(text_color)
            canvas.drawCentredString(page_width/2, page_height - 60, process_text(week_dates))

        # Shifts (headers)
        shift_headers = {
            'shift_1': '7h à 15h',
            'shift_2': '15h à 23h',
            'shift_3': '23h à 7h',
            'shift_4': '7h à 19h',
            'shift_5': '19h à 7h',
            'shift_6': '9h à 17h'
        }
        
        # Determine active shifts
        #Only keep shifts that have at least one operator assigned
        active_shifts = []
        for shift_key, shift_name in shift_headers.items():
            if any(row[shift_key] for row in schedule_data):
                active_shifts.append((shift_key, shift_name))

        # Calculate dimensions for the table
        margin = 40
        available_width = page_width - (2 * margin)
        num_columns = len(active_shifts) + 1
        col_width = available_width / num_columns
        
        # Fixed number of rows per page (13 rows + 1 header row = 14 total)
        rows_per_page = 13
        row_height = min((page_height - 75) / 12, 35)

        # Split data into pages
        pages = []
        current_page = []
        for row in schedule_data:
            if len(current_page) >= rows_per_page:
                pages.append(current_page)
                current_page = []
            current_page.append(row)
        if current_page:
            pages.append(current_page)

        total_pages = len(pages)

        # Generate each page
        for page_num, page_data in enumerate(pages, 1):
            if page_num > 1:
                p.showPage()
                p.setPageSize(landscape(A4))

            add_page_header(p, page_num, total_pages)

            # Prepare table data for this page
            table_data = [['Machine'] + [shift_name for _, shift_name in active_shifts]]
            for row in page_data:
                # Create machine name with article name if available
                machine_name = row['machine_name']
                if row['article_name']:
                    machine_name = f"{machine_name}\n({row['article_name']})"
                
                table_row = [process_text(machine_name, is_machine=True)]
                for shift_key, _ in active_shifts:
                    cell_text = row[shift_key] if row[shift_key] else ""
                    table_row.append(process_text(cell_text))
                table_data.append(table_row)

            # Create table with appropriate styling
            table = Table(
                table_data,
                colWidths=[col_width] * num_columns,
                rowHeights=[row_height] * len(table_data)
            )
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), table_header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (0, -1), 8),  # First column (machine names)
                ('FONTSTYLE', (0, 1), (0, -1), 'UPPERCASE'), #machines uppercase
                ('FONTSIZE', (1, 1), (-1, -1), 7 if name_type == 'latin' else 12),  # Other columns
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ])

            # Add alternating row colors
            for i in range(len(table_data)):
                if i % 2 == 1:  # odd rows
                    table_style.add('BACKGROUND', (0, i), (-1, i), row_color)

            table.setStyle(table_style)

            # Draw table
            table.wrapOn(p, page_width, page_height)
            table_y = page_height - 85 - (len(table_data) * row_height)
            table.drawOn(p, margin, table_y)

        # Save the PDF
        p.save()
        
        # FileResponse
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        buffer.close()
        response.headers['Content-Type'] = 'application/pdf'
        name_suffix = 'ar' if name_type == 'arabic' else 'fr'
        response.headers['Content-Disposition'] = f'attachment; filename=emploi_{name_suffix}_semaine_{week}_{year}.pdf'
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
            sql = "SELECT page_name FROM user_accessible_pages WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            pages = cursor.fetchall()
            return [page['page_name'] for page in pages]
    finally:
        connection.close()

def has_page_access(page):
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True
    accessible_pages = get_user_accessible_pages(current_user.id)
    return page in accessible_pages

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
    finally:
        connection.close()
    return render_template('users.html', users=users)

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
            # Check if username or email exists
            sql = "SELECT id FROM users WHERE username = %s OR email = %s"
            cursor.execute(sql, (data['username'], data['email']))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username or email already exists'})
            
            # Create user
            sql = "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (
                data['username'],
                data['email'],
                generate_password_hash(data['password']),
                data['role']
            ))
            user_id = cursor.lastrowid
            
            # Add accessible pages
            if 'accessible_pages' in data and data['accessible_pages']:
                sql = "INSERT INTO user_accessible_pages (user_id, page_name) VALUES (%s, %s)"
                for page in data['accessible_pages']:
                    cursor.execute(sql, (user_id, page))
            
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
                    sql = "INSERT INTO user_accessible_pages (user_id, page_name) VALUES (%s, %s)"
                    for page in data['accessible_pages']:
                        cursor.execute(sql, (user_id, page))
            
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

if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"Server is starting on http://{local_ip}:8000 ...")
    serve(app, host="0.0.0.0", port=8000)
    
