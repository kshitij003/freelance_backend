"""
ABC/UGC Portal Blueprint
Separate portal for students to check approval status of mentor-reviewed submissions
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import os
import json
import hashlib
import bcrypt
from datetime import datetime

abc_bp = Blueprint('abc', __name__, url_prefix='/abc', template_folder='templates/abc')

DB_FOLDER = 'uploads/db'
ABC_RECORDS_FILE = os.path.join(DB_FOLDER, 'abc_records.json')
ABC_USERS_FILE = os.path.join(DB_FOLDER, 'abc_users.json')

# Ensure data files exist
os.makedirs(DB_FOLDER, exist_ok=True)
for file in [ABC_RECORDS_FILE, ABC_USERS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)


def load_abc_records():
    """Load ABC records from JSON"""
    try:
        with open(ABC_RECORDS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_abc_records(records):
    """Save ABC records to JSON"""
    with open(ABC_RECORDS_FILE, 'w') as f:
        json.dump(records, f, indent=2)


def load_abc_users():
    """Load ABC users from JSON"""
    try:
        with open(ABC_USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_abc_users(users):
    """Save ABC users to JSON"""
    with open(ABC_USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def create_student_account(apaar_id, name, email=''):
    """Auto-create student account when submission approved"""
    users = load_abc_users()
    
    # Check if user exists
    if apaar_id in users:
        return
    
    # Generate default password (APAAR ID for demo)
    default_password = apaar_id
    hashed = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
    
    users[apaar_id] = {
        'apaar_id': apaar_id,
        'name': name,
        'email': email,
        'password_hash': hashed.decode('utf-8'),
        'created_at': datetime.now().isoformat()
    }
    
    save_abc_users(users)


def verify_student_login(apaar_id, password):
    """Verify student login credentials"""
    users = load_abc_users()
    
    if apaar_id not in users:
        return False
    
    user = users[apaar_id]
    stored_hash = user['password_hash'].encode('utf-8')
    
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)


def save_to_abc(internship_id, abc_token, internship_data, approval_data):
    """Save approved submission to ABC portal"""
    records = load_abc_records()
    
    records[internship_id] = {
        'internship_id': internship_id,
        'abc_token': abc_token,
        'apaar_id': internship_data.get('apaar_id', ''),
        'student_name': internship_data.get('name', ''),
        'student_email': internship_data.get('email', ''),
        'organization': internship_data.get('organization', ''),
        'internship_title': internship_data.get('internship_title', ''),
        'start_date': internship_data.get('start_date', ''),
        'end_date': internship_data.get('end_date', ''),
        'hours': internship_data.get('hours', 0),
        'credits_awarded': approval_data.get('credits', 0),
        'matched_course': approval_data.get('top_match', ''),
        'wmd_score': approval_data.get('composite_score', 0),
        'status': 'Approved',
        'approved_by': approval_data.get('approved_by', 'System'),
        'approved_at': datetime.now().isoformat(),
        'report_path': approval_data.get('report_path', ''),
        'notes': approval_data.get('notes', '')
    }
    
    save_abc_records(records)
    
    # Auto-create student account
    create_student_account(
        internship_data.get('apaar_id', ''),
        internship_data.get('name', ''),
        internship_data.get('email', '')
    )
    
    return records[internship_id]


# ============ ROUTES ============

@abc_bp.route('/')
def index():
    """ABC Portal home - redirect to login"""
    if 'abc_student_id' in session:
        return redirect(url_for('abc.dashboard'))
    return redirect(url_for('abc.login'))


@abc_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Student login page"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        apaar_id = data.get('apaar_id', '').strip()
        password = data.get('password', '').strip()
        
        if not apaar_id or not password:
            if request.is_json:
                return jsonify({'success': False, 'error': 'APAAR ID and password are required'}), 400
            return render_template('abc/login.html', error='APAAR ID and password are required')
        
        # Verify credentials
        if verify_student_login(apaar_id, password):
            session['abc_student_id'] = apaar_id
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('abc.dashboard')})
            return redirect(url_for('abc.dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            return render_template('abc/login.html', error='Invalid APAAR ID or password')
    
    # GET request
    if 'abc_student_id' in session:
        return redirect(url_for('abc.dashboard'))
    
    return render_template('abc/login.html')


@abc_bp.route('/logout')
def logout():
    """Student logout"""
    session.pop('abc_student_id', None)
    return redirect(url_for('abc.login'))


@abc_bp.route('/dashboard')
def dashboard():
    """Student dashboard showing approval status"""
    if 'abc_student_id' not in session:
        return redirect(url_for('abc.login'))
    
    apaar_id = session['abc_student_id']
    records = load_abc_records()
    users = load_abc_users()
    
    # Get student info
    student_info = users.get(apaar_id, {})
    
    # Filter records for this student
    student_submissions = []
    for record_id, record in records.items():
        if record.get('apaar_id') == apaar_id:
            student_submissions.append(record)
    
    # Sort by approval date (newest first)
    student_submissions.sort(key=lambda x: x.get('approved_at', ''), reverse=True)
    
    return render_template('abc/dashboard.html', 
                          student=student_info,
                          submissions=student_submissions)


@abc_bp.route('/api/status/<abc_token>')
def get_status(abc_token):
    """API endpoint to check status by ABC token"""
    records = load_abc_records()
    
    # Find record by ABC token
    for record_id, record in records.items():
        if record.get('abc_token') == abc_token:
            return jsonify({
                'success': True,
                'status': 'found',
                'data': record
            })
    
    return jsonify({
        'success': False,
        'status': 'not_found',
        'message': 'No record found with this ABC token'
    }), 404
