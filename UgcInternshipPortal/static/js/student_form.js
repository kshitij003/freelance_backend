// Student Form Page JavaScript

const uploadId = document.getElementById('uploadId').value;
const fromUpload = document.getElementById('fromUpload').value;
const studentForm = document.getElementById('studentForm');
const confidenceIndicator = document.getElementById('confidenceIndicator');
const errorSection = document.getElementById('errorSection');
const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));

let extractedFields = {};
let fieldConfidences = {};
let hasLowConfidence = false;

// Field mapping
const fieldMap = {
    'name': 'name',
    'apaar_id': 'apaarId',
    'institution_code': 'institutionCode',
    'organization': 'organization',
    'internship_title': 'internshipTitle',
    'start_date': 'startDate',
    'end_date': 'endDate',
    'hours': 'hours'
};

// Load extracted data if coming from upload
if (fromUpload === '1' && uploadId) {
    loadExtractedData();
}

async function loadExtractedData() {
    try {
        const response = await fetch(`https://freelance-backend-y0el.onrender.com/api/upload/${uploadId}`);
        const data = await response.json();
        
        extractedFields = data.extracted_fields;
        
        // Auto-fill form with animation
        setTimeout(() => autoFillForm(extractedFields), 300);
        
    } catch (error) {
        console.error('Failed to load extracted data:', error);
    }
}

function autoFillForm(fields) {
    hasLowConfidence = false;
    let allHighConfidence = true;
    
    for (const [apiField, formField] of Object.entries(fieldMap)) {
        if (fields[apiField]) {
            const value = fields[apiField].value;
            const conf = fields[apiField].conf || 0;
            
            const input = document.getElementById(formField);
            const confDiv = document.getElementById(formField + '_conf');
            
            if (value && input) {
                // Animate fill
                input.classList.add('animate-fill');
                input.value = value;
                
                // Store confidence
                fieldConfidences[formField] = conf;
                
                // Show confidence indicator
                if (confDiv) {
                    const confPercent = (conf * 100).toFixed(0);
                    
                    if (conf >= 0.75) {
                        confDiv.className = 'field-confidence confidence-high';
                        confDiv.textContent = `✓ High confidence (${confPercent}%)`;
                    } else if (conf >= 0.5) {
                        confDiv.className = 'field-confidence confidence-medium';
                        confDiv.textContent = `⚠ Medium confidence (${confPercent}%) - Please verify`;
                        input.classList.add('low-confidence-field');
                        hasLowConfidence = true;
                        allHighConfidence = false;
                    } else if (conf > 0) {
                        confDiv.className = 'field-confidence confidence-low';
                        confDiv.textContent = `⚠ Low confidence (${confPercent}%) - Please verify`;
                        input.classList.add('low-confidence-field');
                        hasLowConfidence = true;
                        allHighConfidence = false;
                    }
                }
            }
        }
    }
    
    // Show overall confidence indicator
    if (Object.keys(fields).length > 0) {
        confidenceIndicator.style.display = 'block';
        
        if (allHighConfidence && !hasLowConfidence) {
            confidenceIndicator.className = 'alert confidence-indicator-all-high';
            confidenceIndicator.innerHTML = '<strong>✅ All fields high confidence</strong> - Auto-filled data looks accurate';
        } else {
            confidenceIndicator.className = 'alert confidence-indicator-needs-attention';
            confidenceIndicator.innerHTML = '<strong>⚠️ Some fields require your attention</strong> - Please review and verify highlighted fields';
        }
    }
}

// Mark field as verified when edited
document.querySelectorAll('input, textarea, select').forEach(field => {
    field.addEventListener('change', () => {
        field.classList.remove('low-confidence-field');
        field.classList.add('field-verified');
        
        // Update confidence to 1.0 for verified fields
        fieldConfidences[field.id] = 1.0;
        
        const confDiv = document.getElementById(field.id + '_conf');
        if (confDiv) {
            confDiv.className = 'field-confidence confidence-high';
            confDiv.textContent = '✓ Verified by student';
        }
    });
});

// Form submission
studentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Check if has low confidence fields
    if (hasLowConfidence) {
        // Show confirmation modal
        confirmModal.show();
    } else {
        await submitForm();
    }
});

document.getElementById('confirmSubmit').addEventListener('click', async () => {
    confirmModal.hide();
    await submitForm();
});

async function submitForm() {
    try {
        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        
        // Collect form data
        const formData = {
            upload_id: uploadId,
            name: document.getElementById('name').value,
            apaar_id: document.getElementById('apaarId').value,
            institution_code: document.getElementById('institutionCode').value,
            organization: document.getElementById('organization').value,
            internship_title: document.getElementById('internshipTitle').value,
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value,
            hours: document.getElementById('hours').value,
            level: document.getElementById('level').value,
            logs: document.getElementById('logs').value,
            field_confidences: buildConfidenceObject()
        };
        
        const response = await fetch('https://freelance-backend-y0el.onrender.com/api/submit_internship', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error('Submission failed');
        }
        
        const data = await response.json();
        
        // Redirect to result page
        window.location.href = data.redirect_url;
        
    } catch (error) {
        errorSection.style.display = 'block';
        errorSection.textContent = 'Submission failed: ' + error.message;
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit for Credit Evaluation';
    }
}

function buildConfidenceObject() {
    const result = {};
    
    for (const [apiField, formField] of Object.entries(fieldMap)) {
        if (fieldConfidences[formField] !== undefined) {
            result[apiField] = {
                value: document.getElementById(formField).value,
                conf: fieldConfidences[formField]
            };
        }
    }
    
    return result;
}
