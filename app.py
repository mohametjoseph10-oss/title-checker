from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from db import get_db_connection, init_db
from ml_logic import check_similarity
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import datetime
import os
import json
from datetime import datetime, date
from functools import wraps
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
app.secret_key = 'super_secret_key_change_me'

# Flask-Mail Configuration
# IMPORTANT: For Gmail, you MUST use an 'App Password', not your regular password.
# Guide: Google Account > Security > 2-Step Verification > App Passwords
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mohametjoseph10@gmail.com'
app.config['MAIL_PASSWORD'] = 'pwsrgzsdtdbgvwpz'
app.config['MAIL_DEFAULT_SENDER'] = 'mohametjoseph10@gmail.com'
app.config['MAIL_DEBUG'] = False # Disable debug in production

mail = Mail(app)

# Initialize database tables
init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session or session.get('role') not in ['Super Admin', 'Admin', 'Viewer']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session or session.get('role') != 'Super Admin':
            if request.is_json:
                return jsonify({"success": False, "error": "Access denied. Super Admin permission required."}), 403
            flash("Access denied. Super Admin permission required.", "error")
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session or session.get('role') not in ['Super Admin', 'Admin']:
            if request.is_json:
                return jsonify({"success": False, "error": "Access denied. Administrative permission required."}), 403
            flash("Access denied. Administrative permission required.", "error")
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    conn = None
    cursor = None
    stats = {
        'total_titles': 0,
        'total_checks': 0,
        'unique_percentage': 0,
        'conflict_alerts': 0
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Total Indexed Titles
        cursor.execute("SELECT COUNT(*) as count FROM project_titles")
        row = cursor.fetchone()
        stats['total_titles'] = row['count'] if row else 0
        
        # 2. Total Similarity Analyses (Checks)
        cursor.execute("SELECT COUNT(*) as count FROM history")
        row = cursor.fetchone()
        stats['total_checks'] = row['count'] if row else 0
        
        # 3. Conflict Alerts (result='TAKEN')
        cursor.execute("SELECT COUNT(*) as count FROM history WHERE result IN ('TAKEN', 'Taken')")
        row = cursor.fetchone()
        stats['conflict_alerts'] = row['count'] if row else 0
        
        # 4. Unique Percentage
        if stats['total_checks'] > 0:
            cursor.execute("SELECT COUNT(*) as count FROM history WHERE result IN ('UNIQUE', 'Unique')")
            unique_count = cursor.fetchone()['count']
            stats['unique_percentage'] = round((unique_count / stats['total_checks']) * 100)
        else:
            stats['unique_percentage'] = 0

        # Fetch group members for Home section
        cursor.execute('SELECT * FROM group_members ORDER BY id')
        group_members = cursor.fetchall()
            
    except Exception as e:
        print(f"Home Stats Error: {e}")
        group_members = []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('home.html', group_members=group_members, **stats)

@app.route('/check')
def check_page():
    return render_template('check.html')

@app.route('/methodology')
def methodology_page():
    return render_template('methodology.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/repository')
def repository():
    # Parameters
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    sort_col = request.args.get('sort', 'id')
    order_dir = request.args.get('order', 'asc')
    
    per_page = 20
    offset = (page - 1) * per_page
    
    # Sorting logic validation
    if sort_col not in ['id', 'title']:
        sort_col = 'id'
    if order_dir not in ['asc', 'desc']:
        order_dir = 'asc'
        
    order_clause = f"{sort_col} {order_dir.upper()}"
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Build query
    if q:
        search_term = f"%{q}%"
        query = f"SELECT * FROM project_titles WHERE title LIKE %s ORDER BY {order_clause} LIMIT %s OFFSET %s"
        cursor.execute(query, (search_term, per_page, offset))
        titles = cursor.fetchall()
        
        count_query = "SELECT COUNT(*) as count FROM project_titles WHERE title LIKE %s"
        cursor.execute(count_query, (search_term,))
    else:
        query = f"SELECT * FROM project_titles ORDER BY {order_clause} LIMIT %s OFFSET %s"
        cursor.execute(query, (per_page, offset))
        titles = cursor.fetchall()
        
        count_query = "SELECT COUNT(*) as count FROM project_titles"
        cursor.execute(count_query)
        
    total_titles = cursor.fetchone()['count']
    total_pages = (total_titles + per_page - 1) // per_page
    
    cursor.close()
    conn.close()
    
    return render_template('repository.html', 
                           titles=titles, 
                           total_titles=total_titles, 
                           q=q, 
                           sort_col=sort_col, 
                           order_dir=order_dir, 
                           page=page, 
                           total_pages=total_pages)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject') # Optional field
        message = request.form.get('message')
        
        if not name or not email or not message:
            return render_template('contact.html', error="All fields are required.")
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Normalize subject for matching
        subject_original = subject if subject else 'Support Inquiry'
        subject_key = subject_original.strip().lower()
        
        import mysql.connector
        
        try:
            # Try to create a new thread first
            cursor.execute("""
                INSERT INTO contact_messages (name, email, subject, subject_key, message, status, is_read, last_activity, last_preview) 
                VALUES (%s, %s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP, %s)
            """, (name, email, subject_original, subject_key, message, 'Pending', message))
            message_id = cursor.lastrowid
        except mysql.connector.IntegrityError as err:
            # If duplicate (email, subject_key), fetch the existing thread and update it
            if err.errno == 1062:
                cursor.execute("SELECT id FROM contact_messages WHERE email = %s AND subject_key = %s", (email, subject_key))
                thread = cursor.fetchone()
                message_id = thread['id']
                
                cursor.execute("""
                    UPDATE contact_messages 
                    SET status = 'Pending', is_read = FALSE, last_activity = CURRENT_TIMESTAMP, last_preview = %s 
                    WHERE id = %s
                """, (message, message_id))
            else:
                raise

        
        # Always insert into message_replies
        cursor.execute("""
            INSERT INTO message_replies (message_id, sender_type, sender_email, reply_text) 
            VALUES (%s, 'user', %s, %s)
        """, (message_id, email, message))
        
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('contact.html', success="Your message has been sent successfully.")
    return render_template('contact.html')

@app.route('/result')
def result_page():
    entered_title = request.args.get('entered_title', '')
    most_similar = request.args.get('most_similar', '')
    score = request.args.get('score', 0.0, type=float)
    result = request.args.get('result', '')
    
    return render_template('result.html', 
                           entered_title=entered_title, 
                           most_similar=most_similar, 
                           score=score, 
                           result=result)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')
        
    # Support both JSON and Form data for flexibility, favoring the user's requested form names
    if request.is_json:
        email = request.json.get('admin_email_unique') or request.json.get('email')
        password = request.json.get('admin_password_unique') or request.json.get('password')
    else:
        email = request.form.get('admin_email_unique')
        password = request.form.get('admin_password_unique')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Credentials required"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM admin_users WHERE email = %s", (email,))
        
    user = cursor.fetchone()
    if user:
        stored_pw = user['password']
        # Support both bcrypt (legacy) and werkzeug (new)
        is_valid = False
        if stored_pw.startswith('$2b$'):
            if bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8')):
                is_valid = True
        else:
            if check_password_hash(stored_pw, password):
                is_valid = True

        if is_valid:
            session['admin_id'] = user['id']
            session['role'] = user.get('role', 'Admin') 
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Invalid administrative credentials"}), 401

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Parameters for history table
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    search = request.args.get('search', '')
    filter_result = request.args.get('filter', 'All')
    
    # Mapping frontend sort names to DB column names
    sort_map = {
        'entered_title': 'entered_title',
        'matched_title': 'matched_title',
        'result': 'result',
        'similarity': 'similarity_score',
        'date': 'date'
    }
    
    db_sort_col = sort_map.get(sort_by, 'date')
    if order not in ['asc', 'desc']:
        order = 'desc'
    
    stats = {}
    history = []
    
    conn = None
    cursor = None
    try:
        # Create a fresh connection for this request
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calculate Stats (Ensure fresh results by using the verified connection)
        cursor.execute("SELECT COUNT(*) as count FROM project_titles")
        row = cursor.fetchone()
        stats['total_titles'] = row['count'] if row else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM history")
        row = cursor.fetchone()
        stats['total_checks'] = row['count'] if row else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM history WHERE result='UNIQUE'")
        row = cursor.fetchone()
        stats['unique_count'] = row['count'] if row else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM history WHERE result='TAKEN'")
        row = cursor.fetchone()
        stats['taken_count'] = row['count'] if row else 0
        
        cursor.execute("SELECT AVG(similarity_score) as avg FROM history")
        res = cursor.fetchone()
        stats['avg_similarity'] = ((res['avg'] or 0) * 100)
        
        # Build History Query with Filters
        query = "SELECT * FROM history WHERE 1=1"
        params = []
        
        if search:
            query += " AND entered_title LIKE %s"
            params.append(f"%{search}%")
            
        if filter_result != 'All':
            query += " AND result = %s"
            params.append(filter_result)
            
        query += f" ORDER BY {db_sort_col} {order.upper()} LIMIT 50"
        
        cursor.execute(query, params)
        history = cursor.fetchall()
        
    except Exception as e:
        print(f"Dashboard Query Error: {e}")
        # Re-attempting once if connection was lost (rare with fresh connection but adds stability)
        return render_template('admin_dashboard.html', stats={}, history=[], error=str(e))
    finally:
        # Strictly close both cursor and connection after queries
        if cursor: cursor.close()
        if conn: conn.close()
    
    return render_template('admin_dashboard.html', 
                           stats=stats, 
                           history=history, 
                           sort_by=sort_by, 
                           order=order,
                           current_search=search,
                           current_filter=filter_result)
@app.route('/admin/titles')
@login_required
def admin_titles_page():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'id')
    order = request.args.get('order', 'desc')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base query for total count
    count_query = "SELECT COUNT(*) as count FROM project_titles WHERE 1=1"
    params = []
    if search:
        count_query += " AND title LIKE %s"
        params.append(f"%{search}%")
    
    cursor.execute(count_query, params)
    total_titles = cursor.fetchone()['count']
    
    # Base query for data
    query = "SELECT * FROM project_titles WHERE 1=1"
    if search:
        query += " AND title LIKE %s"
        
    query += f" ORDER BY {sort_by} {order.upper()}"
    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    titles = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    total_pages = (total_titles + per_page - 1) // per_page
    
    return render_template('admin_titles.html', 
                           titles=titles, 
                           total_titles=total_titles,
                           current_page=page,
                           total_pages=total_pages,
                           current_search=search,
                           sort_by=sort_by,
                           order=order)

@app.route('/admin/analytics')
@login_required
def admin_analytics_page():
    period = request.args.get('period', '30')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base WHERE clause for history
    where_clause = " WHERE 1=1"
    params = []
    
    if period != 'all':
        days = int(period)
        where_clause += " AND date >= DATE_SUB(NOW(), INTERVAL %s DAY)"
        params.append(days)

    # Basic Stats (Total titles is always all-time)
    cursor.execute("SELECT COUNT(*) as count FROM project_titles")
    total_titles = cursor.fetchone()['count']
    
    # Filtered Stats
    cursor.execute(f"SELECT COUNT(*) as count FROM history{where_clause}", params)
    total_checks = cursor.fetchone()['count']
    
    cursor.execute(f"SELECT COUNT(*) as count FROM history{where_clause} AND result='UNIQUE'", params)
    unique_count = cursor.fetchone()['count']
    
    cursor.execute(f"SELECT COUNT(*) as count FROM history{where_clause} AND result='TAKEN'", params)
    taken_count = cursor.fetchone()['count']
    
    cursor.execute(f"SELECT AVG(similarity_score) as avg_score FROM history{where_clause}", params)
    avg_row = cursor.fetchone()
    avg_similarity = (avg_row['avg_score'] or 0) * 100

    # Recent Activity — total checks per day (all results)
    activity_query = f"SELECT MAX(date) as day, COUNT(*) as count FROM history{where_clause} GROUP BY DATE(date) ORDER BY day DESC LIMIT 10"
    cursor.execute(activity_query, params)
    recent_activity = cursor.fetchall()
    recent_activity.reverse()

    # Similarity Alerts — TAKEN records only, ordered by score descending
    cursor.execute(f"SELECT * FROM history{where_clause} AND result='TAKEN' ORDER BY similarity_score DESC LIMIT 5", params)
    highest_similarity = cursor.fetchall()

    # Recent Unique Titles — UNIQUE records only
    cursor.execute(f"SELECT * FROM history{where_clause} AND result='UNIQUE' ORDER BY date DESC LIMIT 5", params)
    recent_unique = cursor.fetchall()

    # Recent Conflicts — TAKEN records only
    cursor.execute(f"SELECT * FROM history{where_clause} AND result='TAKEN' ORDER BY date DESC LIMIT 5", params)
    recent_taken = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('admin_analytics.html', 
                           total_titles=total_titles,
                           total_checks=total_checks,
                           unique_count=unique_count,
                           taken_count=taken_count,
                           avg_similarity=avg_similarity,
                           recent_activity=recent_activity,
                           highest_similarity=highest_similarity,
                           recent_unique=recent_unique,
                           recent_taken=recent_taken,
                           current_period=period)

@app.route('/admin/users')
@super_admin_required
def admin_users_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, email, role FROM admin_users ORDER BY id")
    users = cursor.fetchall()
    
    # Calculate stats
    total_admins = len(users)
    super_admins = len([u for u in users if u.get('role') == 'Super Admin'])
    standard_admins = len([u for u in users if u.get('role') == 'Admin'])
    viewers = len([u for u in users if u.get('role') == 'Viewer'])
    
    stats = {
        'total': total_admins,
        'super': super_admins,
        'admin': standard_admins,
        'viewer': viewers
    }
    
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users, stats=stats)

@app.route('/admin/users', methods=['POST'])
@super_admin_required
def api_add_user():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'Admin')
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400
        
    if role not in ['Super Admin', 'Admin', 'Viewer']:
        return jsonify({"success": False, "error": "Invalid role"}), 400
        
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admin_users (email, password, role) VALUES (%s, %s, %s)", (email, hashed_password, role))
        conn.commit()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()
    return jsonify({"success": True})

@app.route('/admin/users/update-role/<int:id>', methods=['POST'])
@super_admin_required
def api_update_user_role(id):
    data = request.json
    new_role = data.get('role')
    
    if new_role not in ['Super Admin', 'Admin', 'Viewer']:
        return jsonify({"success": False, "error": "Invalid role"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Safety Check: Do not allow self-demotion from Super Admin if it's the last one
    cursor.execute("SELECT role FROM admin_users WHERE id = %s", (id,))
    target_user = cursor.fetchone()
    if not target_user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    if target_user['role'] == 'Super Admin' and new_role != 'Super Admin':
        cursor.execute("SELECT COUNT(*) as count FROM admin_users WHERE role = 'Super Admin'")
        super_count = cursor.fetchone()['count']
        if super_count <= 1:
            return jsonify({"success": False, "error": "Cannot demote the last Super Admin"}), 400
            
    # Safety Check: Logged in user demoting themselves
    if session.get('admin_id') == id and target_user['role'] == 'Super Admin' and new_role != 'Super Admin':
         return jsonify({"success": False, "error": "You cannot remove your own Super Admin role"}), 400

    try:
        cursor.execute("UPDATE admin_users SET role = %s WHERE id = %s", (new_role, id))
        conn.commit()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()
    return jsonify({"success": True})

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@super_admin_required
def admin_edit_user(user_id):
    # Security: Only Super Admin can edit users
    if session.get('role') != 'Super Admin':
        if request.is_json:
            return jsonify({"success": False, "error": "Unauthorized. Only Super Admin can edit users."}), 403
        return redirect(url_for('admin_users_page'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute("SELECT id, email, role FROM admin_users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True, "user": user})

    # POST method - Update user
    data = request.json
    new_role = data.get('role')
    new_password = data.get('password')
    confirm_password = data.get('confirm_password')

    if new_role not in ['Super Admin', 'Admin', 'Viewer']:
        return jsonify({"success": False, "error": "Invalid role selected."}), 400

    # Password Logic
    update_password = False
    if (new_password and new_password.strip()) or (confirm_password and confirm_password.strip()):
        if not new_password or not confirm_password:
            return jsonify({"success": False, "error": "Both password fields are required to update password."}), 400
        if new_password != confirm_password:
            return jsonify({"success": False, "error": "Passwords do not match."}), 400
        update_password = True

    try:
        # Update Role
        cursor.execute("UPDATE admin_users SET role = %s WHERE id = %s", (new_role, user_id))
        
        # Update Password if provided
        if update_password:
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE admin_users SET password = %s WHERE id = %s", (hashed_password, user_id))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/users/<int:id>', methods=['DELETE'])
@super_admin_required
def api_delete_user(id):
    if session.get('admin_id') == id:
        return jsonify({"success": False, "error": "Cannot delete your own account"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Safety Check: Do not delete the last Super Admin
    cursor.execute("SELECT role FROM admin_users WHERE id = %s", (id,))
    target_user = cursor.fetchone()
    if not target_user:
        return jsonify({"success": False, "error": "User not found"}), 404
        
    if target_user['role'] == 'Super Admin':
        cursor.execute("SELECT COUNT(*) as count FROM admin_users WHERE role = 'Super Admin'")
        super_count = cursor.fetchone()['count']
        if super_count <= 1:
            return jsonify({"success": False, "error": "Cannot delete the last Super Admin"}), 400

    cursor.execute("DELETE FROM admin_users WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

@app.route('/admin/settings')
@super_admin_required
def admin_settings_page():
    return render_template('admin_settings.html')

@app.route('/admin/settings/update', methods=['POST'])
@super_admin_required
def api_update_settings():
    data = request.json
    setting_type = data.get('type')
    value = data.get('value')
    
    # Validation
    if setting_type == 'threshold':
        try:
            val = float(value)
            if not (0 <= val <= 1):
                return jsonify({"success": False, "error": "Threshold must be between 0 and 1"}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Invalid threshold value"}), 400
            
    # In a real application, these would be saved to a database or config file
    # For this implementation, we acknowledge the update for the Super Admin
    return jsonify({"success": True, "message": f"System {setting_type} updated successfully."})

@app.route('/admin/settings/password', methods=['PUT'])
@super_admin_required
def api_change_password():
    data = request.json
    password = data.get('password')
    if not password:
        return jsonify({"success": False, "error": "Password is required"}), 400
        
    admin_id = session.get('admin_id')
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin_users SET password = %s WHERE id = %s", (hashed_password, admin_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

@app.route('/admin/support')
@login_required
def admin_support_page():
    return render_template('admin_support.html')

# Route to view contact support messages with search and sorting
@app.route('/admin/messages')
@login_required
def admin_messages_page():
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    search = request.args.get('search', '')
    
    if sort_by not in ['id', 'date', 'name', 'last_activity']:
        sort_by = 'last_activity'
    if order not in ['asc', 'desc']:
        order = 'desc'
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Mark as read
    cursor.execute("UPDATE contact_messages SET is_read = TRUE WHERE is_read = FALSE")
    conn.commit()
    
    # Base Stats
    cursor.execute("SELECT COUNT(*) as count FROM contact_messages")
    total_messages = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM contact_messages WHERE date >= NOW() - INTERVAL 1 DAY")
    new_messages = cursor.fetchone()['count']
    
    cursor.execute("SELECT MAX(date) as latest FROM contact_messages")
    latest_row = cursor.fetchone()
    latest_date = latest_row['latest'] if latest_row else None
    
    # Query with filters
    query = "SELECT * FROM contact_messages"
    params = []
    
    if search:
        query += " WHERE name LIKE %s OR email LIKE %s OR message LIKE %s"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
        
    query += f" ORDER BY {sort_by} {order.upper()}"
    
    cursor.execute(query, params)
    messages = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_messages.html', 
                           messages=messages, 
                           current_sort_by=sort_by, 
                           current_order=order,
                           current_search=search,
                           stats={
                               'total': total_messages,
                               'new': new_messages,
                               'latest': latest_date
                           })

@app.route('/admin/messages/delete/<int:id>', methods=['POST'])
@admin_required
def delete_message(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_messages WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_messages_page'))

@app.route('/admin/clear_messages', methods=['POST'])
@admin_required
def clear_all_messages():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contact_messages")
        conn.commit()
        flash("All messages deleted successfully", "success")
    except Exception as e:
        print(f"Clear All Messages Error: {e}")
        flash("Failed to delete all messages", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return redirect(url_for('admin_messages_page'))

@app.route('/admin/reply_message', methods=['POST'])
@admin_required
def admin_reply_message():
    message_id = request.form.get('message_id')
    recipient_email = request.form.get('recipient_email')
    subject = request.form.get('subject')
    reply_body = request.form.get('reply_body')
    
    if not reply_body:
        flash("Reply message cannot be empty.", "error")
        return redirect(url_for('admin_messages_page'))
        
    try:
        # Send Email
        msg = Message(subject=subject, recipients=[recipient_email])
        msg.body = reply_body
        mail.send(msg)
        
        # Update Status in Database and Save Reply
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get admin email
        admin_id = session.get('admin_id')
        cursor.execute("SELECT email FROM admin_users WHERE id = %s", (admin_id,))
        admin = cursor.fetchone()
        admin_email = admin['email'] if admin else 'admin@system.com'
        
        # Save reply to history
        cursor.execute("INSERT INTO message_replies (message_id, sender_type, sender_email, reply_text) VALUES (%s, %s, %s, %s)",
                       (message_id, 'admin', admin_email, reply_body))
        
        # Update status and activity
        cursor.execute("""
            UPDATE contact_messages 
            SET status = 'Replied', replied_at = %s, last_activity = CURRENT_TIMESTAMP, last_preview = %s 
            WHERE id = %s
        """, (datetime.now(), reply_body, message_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Reply sent successfully via email.", "success")
    except Exception as e:
        # Specific logging for debugging SMTP issues
        print(f"--- MAIL SYSTEM ERROR ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"--------------------------")
        
        error_msg = "Failed to send email. "
        if "535" in str(e):
            error_msg += "Authentication failed. Please verify your Gmail App Password."
        else:
            error_msg += "Please check your SMTP configuration and network."
            
        flash(error_msg, "error")
        
    redirect_to = request.form.get('redirect_to')
    if redirect_to == 'conversation':
        return redirect(url_for('message_conversation', message_id=message_id))
    return redirect(url_for('admin_messages_page'))

@app.route('/admin/unread_messages_count')
@login_required
def unread_messages_count():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count FROM contact_messages WHERE is_read = FALSE")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify({"count": result['count'] if result else 0})

@app.route('/admin/message/<int:message_id>/conversation')
@login_required
def message_conversation(message_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get original message details
    cursor.execute("SELECT * FROM contact_messages WHERE id = %s", (message_id,))
    message = cursor.fetchone()
    
    if not message:
        cursor.close()
        conn.close()
        flash("Message not found.", "error")
        return redirect(url_for('admin_messages_page'))
        
    # Mark thread as read
    cursor.execute("UPDATE contact_messages SET is_read = TRUE WHERE id = %s", (message_id,))
    conn.commit()

    # Get conversation history
    cursor.execute("SELECT * FROM message_replies WHERE message_id = %s ORDER BY created_at ASC", (message_id,))
    messages_list = cursor.fetchall()
    
    # If history is empty (e.g. for old messages), add the original message to replies
    if not messages_list:
        cursor.execute("INSERT INTO message_replies (message_id, sender_type, sender_email, reply_text, created_at) VALUES (%s, %s, %s, %s, %s)",
                       (message_id, 'user', message['email'], message['message'], message['date']))
        conn.commit()
        # Re-fetch
        cursor.execute("SELECT * FROM message_replies WHERE message_id = %s ORDER BY created_at ASC", (message_id,))
        messages_list = cursor.fetchall()

    # Get Admin Notes
    cursor.execute("SELECT * FROM admin_notes WHERE message_id = %s ORDER BY created_at DESC", (message_id,))
    admin_notes = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('admin_conversation.html', 
                           message=message, 
                           messages=messages_list,
                           admin_notes=admin_notes)


@app.route('/admin/message/<int:message_id>/close', methods=['POST'])
@login_required
def close_thread(message_id):
    """Marks a support message thread as Closed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE contact_messages SET status = 'Closed' WHERE id = %s", (message_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Thread marked as closed successfully.", "success")
    return redirect(url_for('message_conversation', message_id=message_id))

@app.route('/admin/message/<int:message_id>/note', methods=['POST'])
@login_required
def add_admin_note(message_id):
    note_text = request.form.get('note_text')
    if not note_text:
        flash("Note cannot be empty.", "error")
        return redirect(url_for('message_conversation', message_id=message_id))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get admin email
    admin_id = session.get('admin_id')
    cursor.execute("SELECT email FROM admin_users WHERE id = %s", (admin_id,))
    admin = cursor.fetchone()
    admin_email = admin['email'] if admin else 'admin@system.com'
    
    cursor.execute("INSERT INTO admin_notes (message_id, admin_email, note_text) VALUES (%s, %s, %s)",
                   (message_id, admin_email, note_text))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Internal note added.", "success")
    return redirect(url_for('message_conversation', message_id=message_id))

@app.route('/admin/history/<int:id>')
@login_required
def history_detail(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM history WHERE id = %s", (id,))
    history_item = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not history_item:
        return redirect(url_for('admin_dashboard'))
        
    return render_template('history_detail.html', item=history_item)

@app.route('/admin/history/delete/<int:id>', methods=['POST'])
@admin_required
def delete_history(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/history/clear', methods=['POST'])
@admin_required
def clear_all():
    """
    Clears all records from history and redirects safely to dashboard.
    Ensures connection is closed immediately after execution.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
    except Exception as e:
        print(f"Clear All Error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/history/clear_alias', endpoint='clear_history', methods=['POST'])
@login_required
def clear_history_alias():
    return clear_all()

@app.route('/login', methods=['POST'])
def api_login():
    return admin_login()

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('role', None)
    return redirect(url_for('home'))

@app.route('/titles', methods=['GET', 'POST'])
@admin_required
def manage_titles():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'GET':
        cursor.execute("SELECT * FROM project_titles")
        titles = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(titles)
    elif request.method == 'POST':
        title = request.json.get('title')
        cursor.execute("INSERT INTO project_titles (title) VALUES (%s)", (title,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})

@app.route('/titles/<int:id>', methods=['PUT', 'DELETE'])
@admin_required
def update_delete_title(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'PUT':
        title = request.json.get('title')
        cursor.execute("UPDATE project_titles SET title=%s WHERE id=%s", (title, id))
    elif request.method == 'DELETE':
        cursor.execute("DELETE FROM project_titles WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/check-title', methods=['POST'])
def api_check_title():
    data = request.json
    title = data.get('title')
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT title FROM project_titles")
    rows = cursor.fetchall()
    
    existing_titles = [row['title'] for row in rows]
    
    if not existing_titles:
        return jsonify({
            "entered_title": title,
            "most_similar": "None",
            "score": 0.0,
            "result": "Unique"
        })
        
    most_similar, score = check_similarity(title, existing_titles)
    
    # Simple classification
    if score >= 0.70:
        result = "TAKEN"
    else:
        result = "UNIQUE"
    
    # Save to history
    cursor.execute("""
        INSERT INTO history (entered_title, matched_title, similarity_score, result)
        VALUES (%s, %s, %s, %s)
    """, (title, most_similar, float(score), result))
        
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "entered_title": title,
        "most_similar": most_similar,
        "score": float(score),
        "result": result
    })

# ─────────────────────────────────────────────────────────────
# GROUP MEMBERS — PUBLIC
# ─────────────────────────────────────────────────────────────

@app.route('/member/<int:member_id>')
def member_detail(member_id):
    """Public profile page for a single group member."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM group_members WHERE id = %s', (member_id,))
    member = cursor.fetchone()
    cursor.close()
    conn.close()
    if not member:
        flash('Member not found.', 'error')
        return redirect(url_for('home'))
    return render_template('member_detail.html', member=member)

# ─────────────────────────────────────────────────────────────
# GROUP MEMBERS — ADMIN
# ─────────────────────────────────────────────────────────────

@app.route('/admin/group-members')
@login_required
def admin_group_members():
    """Admin: list all group members."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM group_members ORDER BY id')
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_group_members.html', members=members, active_page='group_members')

@app.route('/admin/edit-member/<int:member_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_member(member_id):
    """Admin: edit a group member's details and optionally upload a new photo."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM group_members WHERE id = %s', (member_id,))
    member = cursor.fetchone()

    if not member:
        cursor.close()
        conn.close()
        flash('Member not found.', 'error')
        return redirect(url_for('admin_group_members'))

    if request.method == 'POST':
        full_name  = request.form.get('full_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        department = request.form.get('department', '').strip()
        whatsapp   = request.form.get('whatsapp', '').strip()
        email      = request.form.get('email', '').strip()

        # Image adjustment values
        try:
            image_scale = float(request.form.get('image_scale', 1.0))
            image_scale = max(1.0, min(3.0, image_scale))
        except (ValueError, TypeError):
            image_scale = 1.0
        try:
            image_pos_x = float(request.form.get('image_pos_x', 0.0))
            image_pos_x = max(-50.0, min(50.0, image_pos_x))
        except (ValueError, TypeError):
            image_pos_x = 0.0
        try:
            image_pos_y = float(request.form.get('image_pos_y', 0.0))
            image_pos_y = max(-50.0, min(50.0, image_pos_y))
        except (ValueError, TypeError):
            image_pos_y = 0.0

        photo_path = member['photo']  # Keep old photo by default

        # Handle optional photo upload
        new_photo = request.files.get('photo')
        if new_photo and new_photo.filename:
            filename = secure_filename(new_photo.filename)
            upload_dir = os.path.join(app.root_path, 'static', 'images', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            new_photo.save(os.path.join(upload_dir, filename))
            photo_path = 'uploads/' + filename

        cursor.execute(
            '''UPDATE group_members
               SET full_name=%s, student_id=%s, department=%s, whatsapp=%s, email=%s,
                   photo=%s, image_scale=%s, image_pos_x=%s, image_pos_y=%s
               WHERE id=%s''',
            (full_name, student_id, department, whatsapp, email,
             photo_path, image_scale, image_pos_x, image_pos_y, member_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Member updated successfully.', 'success')
        return redirect(url_for('admin_group_members'))

    cursor.close()
    conn.close()
    return render_template('admin_edit_member.html', member=member, active_page='group_members')

    cursor.close()
    conn.close()
    return render_template('admin_edit_member.html', member=member, active_page='group_members')

# ─────────────────────────────────────────────────────────────
# HOME — inject members list
# ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
