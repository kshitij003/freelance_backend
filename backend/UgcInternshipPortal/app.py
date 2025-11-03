"""
UGC Internship Credit Portal - Main Flask Application
Full-stack demo with certificate auto-extraction and credit matching
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import os
import json
import hashlib
from datetime import datetime
import uuid

from extractor import extract_from_file, extract_from_text
from ceescm import get_sample_ceescm_tokens
from wmd_matcher import match_internship, WMDMatcher
from report_generator import generate_pdf_report
from abc_portal import abc_bp, save_to_abc

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

# Register ABC Portal Blueprint
app.register_blueprint(abc_bp)

# Configuration
UPLOAD_FOLDER = 'uploads/files'
DB_FOLDER = 'uploads/db'
REPORTS_FOLDER = 'uploads/reports'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'docx'}

# Ensure directories exist
for folder in [UPLOAD_FOLDER, DB_FOLDER, REPORTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Mentor credentials (hardcoded for demo)
MENTOR_USERNAME = 'mentor'
MENTOR_PASSWORD = 'mentorpass'


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_all_confidences(extracted_fields):
    """Get list of confidence scores from extracted fields"""
    confs = []
    for field, data in extracted_fields.items():
        if isinstance(data, dict) and 'conf' in data:
            confs.append(data['conf'])
    return confs


def check_needs_review(extracted_fields, wmd_composite):
    """Check if submission needs mentor review"""
    # Check mandatory field confidences
    mandatory_fields = ['name', 'start_date', 'end_date']
    for field in mandatory_fields:
        if field in extracted_fields:
            conf = extracted_fields[field].get('conf', 0.0)
            if conf < 0.75:
                return True
    
    # Check WMD composite score
    if wmd_composite < 0.55:
        return True
    
    return False


# ============ ROUTES ============

@app.route('/')
def home():
    """Home page"""
    return render_template('home.html')


@app.route('/upload')
def upload_page():
    """File upload page"""
    return render_template('upload.html')


@app.route('/student_form')
def student_form():
    """Student form page"""
    upload_id = request.args.get('upload_id', '')
    from_upload = request.args.get('from_upload', '0')
    return render_template('student_form.html', upload_id=upload_id, from_upload=from_upload)


@app.route('/mentor')
def mentor_page():
    """Mentor login page"""
    if 'mentor_logged_in' in session and session['mentor_logged_in']:
        return redirect(url_for('mentor_dashboard'))
    return render_template('mentor_login.html')


@app.route('/mentor/dashboard')
def mentor_dashboard():
    """Mentor dashboard"""
    if 'mentor_logged_in' not in session or not session['mentor_logged_in']:
        return redirect(url_for('mentor_page'))
    
    # Load submissions that need review
    submissions = []
    for filename in os.listdir(DB_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(DB_FOLDER, filename), 'r') as f:
                data = json.load(f)
                if data.get('needs_review', False):
                    submissions.append(data)
    
    # Sort by timestamp descending
    submissions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return render_template('mentor_dashboard.html', submissions=submissions)


@app.route('/result/<internship_id>')
def result_page(internship_id):
    """Student result page"""
    filepath = os.path.join(DB_FOLDER, f"{internship_id}.json")
    if not os.path.exists(filepath):
        return "Internship not found", 404
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return render_template('result.html', data=data, internship_id=internship_id)


# ============ API ENDPOINTS ============

@app.route('/api/upload_certificate', methods=['POST'])
def upload_certificate():
    """
    Upload and extract certificate fields
    Accepts: multipart file or JSON with 'text' field
    Returns: upload_id and extracted fields with confidences
    """
    upload_id = str(uuid.uuid4())
    extracted_fields = {}
    
    try:
        # Check if file upload or text paste
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{upload_id}_{timestamp}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Extract fields from file
                extracted_fields = extract_from_file(filepath)
                
                # Store metadata
                metadata = {
                    'upload_id': upload_id,
                    'filename': filename,
                    'filepath': filepath,
                    'timestamp': timestamp,
                    'extracted_fields': extracted_fields
                }
        
        elif request.is_json and 'text' in request.json:
            # Text paste
            text = request.json['text']
            extracted_fields = extract_from_text(text)
            
            # Store text
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            text_filename = f"{upload_id}_{timestamp}_pasted.txt"
            text_filepath = os.path.join(UPLOAD_FOLDER, text_filename)
            with open(text_filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            
            metadata = {
                'upload_id': upload_id,
                'filename': text_filename,
                'filepath': text_filepath,
                'timestamp': timestamp,
                'extracted_fields': extracted_fields
            }
        
        else:
            return jsonify({'error': 'No file or text provided'}), 400
        
        # Save metadata
        metadata_path = os.path.join(DB_FOLDER, f"{upload_id}_upload.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            'upload_id': upload_id,
            'extracted_fields': extracted_fields,
            'redirect_url': f'/student_form?upload_id={upload_id}&from_upload=1'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/<upload_id>', methods=['GET'])
def get_upload(upload_id):
    """Get upload metadata and extracted fields"""
    metadata_path = os.path.join(DB_FOLDER, f"{upload_id}_upload.json")
    
    if not os.path.exists(metadata_path):
        return jsonify({'error': 'Upload not found'}), 404
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return jsonify(metadata)


@app.route('/api/submit_internship', methods=['POST'])
def submit_internship():
    """
    Submit completed internship form
    Runs full pipeline: CEESCM -> WMD -> Credit Computation -> ABC (conditional)
    """
    try:
        data = request.json
        
        # Generate internship ID
        internship_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Extract form data
        form_data = {
            'name': data.get('name', ''),
            'apaar_id': data.get('apaar_id', ''),
            'institution_code': data.get('institution_code', ''),
            'organization': data.get('organization', ''),
            'internship_title': data.get('internship_title', ''),
            'start_date': data.get('start_date', ''),
            'end_date': data.get('end_date', ''),
            'hours': data.get('hours', ''),
            'level': data.get('level', ''),
            'logs': data.get('logs', ''),
        }
        
        # Get field confidences if available
        field_confidences = data.get('field_confidences', {})
        
        # CEESCM Tokenization
        ceescm_tokens = get_sample_ceescm_tokens(form_data)
        
        # WMD Matching
        matches, wmd_composite, decision = match_internship(ceescm_tokens)
        
        # Calculate credits based on hours and decision
        hours = int(form_data.get('hours', 0)) if form_data.get('hours') else 0
        credits = 0
        eligible = False
        
        if decision == 'Equivalent':
            credits = min(hours // 40, 4)  # 1 credit per 40 hours, max 4
            eligible = True
        elif decision == 'Partially Equivalent':
            credits = min(hours // 60, 2)  # Partial credits
            eligible = False
        else:
            credits = 0
            eligible = False
        
        # Check if needs review
        needs_review = check_needs_review(field_confidences, wmd_composite)
        
        # Determine auto-push to ABC
        auto_push = False
        abc_token = None
        abc_status = None
        
        if decision == 'Equivalent' and eligible and not needs_review:
            # Auto push to ABC simulator
            min_conf = min(get_all_confidences(field_confidences)) if field_confidences else 1.0
            if min_conf >= 0.75:
                abc_payload = {
                    'student_name': form_data['name'],
                    'apaar_id': form_data['apaar_id'],
                    'credits': credits,
                    'internship_id': internship_id,
                    'timestamp': timestamp
                }
                abc_response = push_to_abc_simulator(abc_payload)
                abc_token = abc_response['abc_token']
                abc_status = abc_response['status']
                auto_push = True
                
                # Save to ABC Portal for student access
                approval_data = {
                    'credits': credits,
                    'top_match': matches[0]['course_id'] if matches else 'Unknown',
                    'composite_score': wmd_composite,
                    'approved_by': 'System (Auto-approved)',
                    'report_path': f'uploads/reports/{internship_id}.pdf',
                    'notes': 'Automatically approved - high confidence submission'
                }
                save_to_abc(internship_id, abc_token, form_data, approval_data)
        
        # Create internship record
        record = {
            'internship_id': internship_id,
            'timestamp': timestamp,
            'form_data': form_data,
            'field_confidences': field_confidences,
            'upload_id': data.get('upload_id', ''),
            'ceescm_tokens': ceescm_tokens,
            'wmd_matches': matches,
            'wmd_composite': wmd_composite,
            'decision': decision,
            'credits': credits,
            'eligible': eligible,
            'needs_review': needs_review,
            'auto_push': auto_push,
            'abc_token': abc_token,
            'abc_status': abc_status,
            'changelog': [
                {
                    'timestamp': timestamp,
                    'action': 'created',
                    'by': 'student'
                }
            ]
        }
        
        # Save record
        record_path = os.path.join(DB_FOLDER, f"{internship_id}.json")
        with open(record_path, 'w') as f:
            json.dump(record, f, indent=2)
        
        # Generate PDF report
        generate_pdf_report(record, os.path.join(REPORTS_FOLDER, f"{internship_id}.pdf"))
        
        return jsonify({
            'internship_id': internship_id,
            'decision': decision,
            'credits': credits,
            'needs_review': needs_review,
            'abc_token': abc_token,
            'redirect_url': f'/result/{internship_id}'
        })
    
    except Exception as e:
        print(f"Error in submit_internship: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/internship/<internship_id>', methods=['GET'])
def get_internship(internship_id):
    """Get internship record with full audit trail"""
    record_path = os.path.join(DB_FOLDER, f"{internship_id}.json")
    
    if not os.path.exists(record_path):
        return jsonify({'error': 'Internship not found'}), 404
    
    with open(record_path, 'r') as f:
        record = json.load(f)
    
    return jsonify(record)


@app.route('/api/mentor/login', methods=['POST'])
def mentor_login():
    """Mentor login"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == MENTOR_USERNAME and password == MENTOR_PASSWORD:
        session['mentor_logged_in'] = True
        return jsonify({'success': True, 'redirect_url': '/mentor/dashboard'})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401


@app.route('/api/mentor/logout', methods=['POST'])
def mentor_logout():
    """Mentor logout"""
    session.pop('mentor_logged_in', None)
    return jsonify({'success': True})


@app.route('/api/mentor/run_and_push', methods=['POST'])
def mentor_run_and_push():
    """Mentor: re-run matching with optional keywords and push to ABC"""
    if 'mentor_logged_in' not in session or not session['mentor_logged_in']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        internship_id = data.get('internship_id')
        custom_keywords = data.get('custom_keywords', [])
        push_to_abc = data.get('push_to_abc', False)
        
        # Load record
        record_path = os.path.join(DB_FOLDER, f"{internship_id}.json")
        with open(record_path, 'r') as f:
            record = json.load(f)
        
        # Add custom keywords to matcher if provided
        if custom_keywords:
            matcher = WMDMatcher()
            # Add keywords to relevant courses
            for match in record.get('wmd_matches', []):
                matcher.add_custom_keywords(match['course_id'], custom_keywords)
            
            # Re-run matching
            ceescm_tokens = record['ceescm_tokens'] + custom_keywords
            matches, wmd_composite, decision = match_internship(ceescm_tokens)
            
            # Update record
            record['wmd_matches'] = matches
            record['wmd_composite'] = wmd_composite
            record['decision'] = decision
            record['needs_review'] = False
            
            # Recalculate credits
            hours = int(record['form_data'].get('hours', 0)) if record['form_data'].get('hours') else 0
            if decision == 'Equivalent':
                record['credits'] = min(hours // 40, 4)
                record['eligible'] = True
            elif decision == 'Partially Equivalent':
                record['credits'] = min(hours // 60, 2)
                record['eligible'] = False
            else:
                record['credits'] = 0
                record['eligible'] = False
        
        # Push to ABC if requested
        if push_to_abc:
            abc_payload = {
                'student_name': record['form_data']['name'],
                'apaar_id': record['form_data']['apaar_id'],
                'credits': record['credits'],
                'internship_id': internship_id,
                'timestamp': datetime.now().isoformat()
            }
            abc_response = push_to_abc_simulator(abc_payload)
            record['abc_token'] = abc_response['abc_token']
            record['abc_status'] = abc_response['status']
            record['auto_push'] = False
            record['needs_review'] = False
            
            # Save to ABC Portal for student access
            approval_data = {
                'credits': record['credits'],
                'top_match': record['wmd_matches'][0]['course_id'] if record.get('wmd_matches') else 'Unknown',
                'composite_score': record['wmd_composite'],
                'approved_by': 'Mentor',
                'report_path': record.get('report_path', ''),
                'notes': 'Reviewed and approved by mentor'
            }
            save_to_abc(internship_id, record['abc_token'], record['form_data'], approval_data)
        
        # Add changelog
        record['changelog'].append({
            'timestamp': datetime.now().isoformat(),
            'action': 'mentor_review',
            'by': 'mentor',
            'changes': {
                'custom_keywords': custom_keywords,
                'pushed_to_abc': push_to_abc
            }
        })
        
        # Save updated record
        with open(record_path, 'w') as f:
            json.dump(record, f, indent=2)
        
        return jsonify({'success': True, 'record': record})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/abc/upload', methods=['POST'])
def abc_upload_internal():
    """Internal ABC simulator connector"""
    return push_to_abc_simulator(request.json)


@app.route('/api/abc/status/<abc_token>', methods=['GET'])
def abc_status(abc_token):
    """Get ABC submission status"""
    # Simulate status check
    return jsonify({
        'abc_token': abc_token,
        'status': 'processed',
        'message': 'Credits successfully registered in ABC system (simulated)'
    })


@app.route('/api/delete_data/<internship_id>', methods=['DELETE'])
def delete_data(internship_id):
    """Delete internship data (student privacy)"""
    try:
        # Delete record
        record_path = os.path.join(DB_FOLDER, f"{internship_id}.json")
        if os.path.exists(record_path):
            os.remove(record_path)
        
        # Delete report
        report_path = os.path.join(REPORTS_FOLDER, f"{internship_id}.pdf")
        if os.path.exists(report_path):
            os.remove(report_path)
        
        return jsonify({'success': True, 'message': 'Data deleted successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download_report/<internship_id>', methods=['GET'])
def download_report(internship_id):
    """Download PDF report"""
    report_path = os.path.join(REPORTS_FOLDER, f"{internship_id}.pdf")
    
    if not os.path.exists(report_path):
        return "Report not found", 404
    
    return send_file(report_path, as_attachment=True, download_name=f"internship_report_{internship_id}.pdf")


# ============ ABC SIMULATOR ============

def push_to_abc_simulator(payload):
    """
    Simulate ABC API upload
    Returns deterministic token based on payload hash
    """
    # Create deterministic token
    payload_str = json.dumps(payload, sort_keys=True)
    hash_obj = hashlib.sha256(payload_str.encode())
    token = 'ABC-TOK-' + hash_obj.hexdigest()[:12].upper()
    
    return {
        'abc_token': token,
        'status': 'accepted',
        'message': 'Credit submission accepted (simulated)',
        'timestamp': datetime.now().isoformat()
    }


# ============ RUN ============

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
