import os
import hashlib
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title='Praktiki Internship API - Final')

# Read allowed origins from environment variable (comma-separated).
# Example: ALLOWED_ORIGINS=https://myapp.vercel.app,https://www.mydomain.com
origins_env = os.getenv(
    'ALLOWED_ORIGINS', 
    'https://www.gvwelkin.com,https://trial3-abc.vercel.app'
)
origins = [o.strip() for o in origins_env.split(',') if o.strip()]
# For demo convenience, if ALLOWED_ORIGINS contains the single value "ALL", allow all.
if len(origins) == 1 and origins[0].upper() == 'ALL':
    allow_origins = ['*']
else:
    allow_origins = origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Demo users (in-memory). Replace with real auth in production.
USERS = {
    "student": {"username": "student", "password": "12345", "role": "student"},
    "mentor": {"username": "mentor", "password": "admin", "role": "mentor"}
}

# In-memory stores (demo)
INTERNSHIPS = {}
WMD_RUNS = {}
ABC_SUBMISSIONS = {}

class InternshipSubmission(BaseModel):
    apaar_id: str
    student_name: str
    institution_code: str
    organization: str
    title: Optional[str] = ''
    start_date: str
    end_date: str
    total_hours: int
    internship_text: str
    level: Optional[str] = 'UG'

def make_internship_id():
    return 'INT-' + hashlib.sha1(str(datetime.utcnow()).encode()).hexdigest()[:9].upper()

def deterministic_token(payload):
    s = json.dumps(payload, sort_keys=True).encode()
    return 'ABC-TOK-' + hashlib.sha256(s).hexdigest()[:12]

@app.get('/health')
def health():
    return {'status': 'ok', 'time': datetime.utcnow().isoformat()}

@app.post('/login')
async def login(request: Request):
    """Accepts form-encoded or JSON body with username & password."""
    content_type = request.headers.get('content-type', '')
    username = password = None
    if 'application/json' in content_type:
        body = await request.json()
        username = body.get('username')
        password = body.get('password')
    else:
        form = await request.form()
        username = form.get('username')
        password = form.get('password')

    if not username or not password:
        raise HTTPException(status_code=400, detail='username and password required')

    user = USERS.get(username)
    if not user or user.get('password') != password:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return {'username': username, 'role': user['role']}

@app.post('/submit_internship')
def submit_internship(payload: InternshipSubmission):
    internship_id = make_internship_id()
    rec = payload.dict()
    rec.update({'internship_id': internship_id, 'status':'PENDING', 'created_at': datetime.utcnow().isoformat()})
    INTERNSHIPS[internship_id] = rec
    return {'internship_id': internship_id, 'status': 'PENDING'}

@app.post('/mentor/run_and_push/{internship_id}')
def mentor_run_and_push(internship_id: str, keywords: Optional[str] = None, mode: str = 'success'):
    # allow lookup by APAAR id too
    if internship_id not in INTERNSHIPS:
        for k,v in INTERNSHIPS.items():
            if v.get('apaar_id') == internship_id:
                internship_id = k
                break
    if internship_id not in INTERNSHIPS:
        raise HTTPException(status_code=404, detail='internship not found')

    intern = INTERNSHIPS[internship_id]
    refs = [
        {'ref_id':'UGC-INT-CLOUD-01','title':'Cloud Infra Deployment','descriptor_text':'deploy cloud infra','min_hours':120},
        {'ref_id':'UGC-INT-DEVOPS-02','title':'CI/CD & Monitoring','descriptor_text':'ci cd monitoring','min_hours':120},
        {'ref_id':'UGC-INT-GENERIC-05','title':'Workplace Exposure','descriptor_text':'workplace exposure','min_hours':60},
    ]
    top_matches = []
    for r in refs:
        wmd = 0.8 if (keywords and r['ref_id'].lower().find((keywords or '').lower().strip())!=-1) or (r['title'].lower() in intern['internship_text'].lower()) else 0.6
        composite = round(wmd*0.6 + 0.4,3)
        decision = 'Equivalent' if composite>=0.72 else ('Partially Equivalent' if composite>=0.55 else 'Not Equivalent')
        top_matches.append({'ref_id': r['ref_id'],'title':r['title'],'wmd':wmd,'composite':composite,'decision':decision})
    WMD_RUNS[internship_id] = {'run_at': datetime.utcnow().isoformat(), 'matches': top_matches}
    try:
        duration_weeks = max(1, int((datetime.fromisoformat(intern['end_date']) - datetime.fromisoformat(intern['start_date'])).days/7))
    except Exception:
        duration_weeks = 1
    credit_value = min(round(intern.get('total_hours',0)/120),6)
    payload = {'apaAR_id': intern['apaar_id'], 'internship_course_code':'INT-2025-001', 'total_hours': intern.get('total_hours',0), 'credit_value': credit_value, 'duration_weeks': duration_weeks, 'learning_outcomes':[top_matches[0]['title']]}
    token = deterministic_token(payload)
    status = 'UPLOADED' if mode=='success' else ('PENDING' if mode=='pending' else 'ERROR')
    ABC_SUBMISSIONS[internship_id] = {'payload': payload, 'mode': mode, 'token': token, 'status': status}
    INTERNSHIPS[internship_id].update({'status': status, 'abc_token': token if status!='ERROR' else None, 'credit_value': credit_value})
    return {'top_matches': top_matches, 'abc_result': {'status': status, 'abc_token': token if status!='ERROR' else None}, 'credit_value': credit_value}

@app.post('/api/v2/credits/upload')
def abc_upload(payload: dict, mode: str = 'success'):
    token = deterministic_token(payload)
    status = 'UPLOADED' if mode=='success' else ('PENDING' if mode=='pending' else 'ERROR')
    return {'status': status, 'abc_token': token, 'received_at': datetime.utcnow().isoformat()}

@app.get('/api/v2/credits/status/{abc_token}')
def abc_status(abc_token: str):
    for k,v in ABC_SUBMISSIONS.items():
        if v.get('token')==abc_token:
            return {'abc_token': abc_token, 'status': v.get('status')}
    return {'abc_token': abc_token, 'status': 'UNKNOWN'}
