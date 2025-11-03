// Upload Certificate Page JavaScript

const extractBtn = document.getElementById('extractBtn');
const certificateFile = document.getElementById('certificateFile');
const certificateText = document.getElementById('certificateText');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const errorSection = document.getElementById('errorSection');

extractBtn.addEventListener('click', async () => {
    // Validate input
    const hasFile = certificateFile.files.length > 0;
    const hasText = certificateText.value.trim().length > 0;
    
    if (!hasFile && !hasText) {
        showError('Please upload a file or paste certificate text');
        return;
    }
    
    if (hasFile && hasText) {
        showError('Please use either file upload or text paste, not both');
        return;
    }
    
    // Show progress
    errorSection.style.display = 'none';
    progressSection.style.display = 'block';
    extractBtn.disabled = true;
    
    try {
        // Step 1: Received
        updateProgress(25, 'Received → Processing...');
        await sleep(500);
        
        // Step 2: OCR/Reading
        updateProgress(50, 'OCR → Extracting text...');
        await sleep(800);
        
        // Prepare and send request
        let response;
        
        if (hasFile) {
            const formData = new FormData();
            formData.append('file', certificateFile.files[0]);
            
            response = await fetch('https://freelance-backend-y0el.onrender.com/api/upload_certificate', {
                method: 'POST',
                body: formData
            });
        } else {
            response = await fetch('https://freelance-backend-y0el.onrender.com/api/upload_certificate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: certificateText.value})
            });
        }
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        // Step 3: Extracting fields
        updateProgress(75, 'Extracting fields → Analyzing...');
        await sleep(600);
        
        const data = await response.json();
        
        // Step 4: Done
        updateProgress(100, 'Done → Redirecting...');
        await sleep(500);
        
        // Redirect to student form
        window.location.href = data.redirect_url;
        
    } catch (error) {
        showError('Extraction failed: ' + error.message);
        progressSection.style.display = 'none';
        extractBtn.disabled = false;
    }
});

function updateProgress(percent, text) {
    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    progressText.textContent = text;
}

function showError(message) {
    errorSection.style.display = 'block';
    errorSection.textContent = message;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
