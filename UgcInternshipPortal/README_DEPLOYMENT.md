# Quick Deployment Guide

## TL;DR: Deploy This Folder to Render

This **entire folder** (`backend/UgcInternshipPortal/`) should be deployed as a **single web service** on Render.

---

## Render Deployment Steps

1. **Push to Git** (GitHub/GitLab/Bitbucket)

2. **Go to Render Dashboard** → New Web Service

3. **Connect your repo**

4. **Configure:**
   - **Name:** `ugc-internship-portal`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python -m spacy download en_core_web_sm || true`
   - **Start Command:** `gunicorn app:app --config gunicorn_config.py`
   - **Root Directory:** `backend/UgcInternshipPortal/` ⚠️ CRITICAL

5. **Environment Variables:**
   ```
   SESSION_SECRET=your-random-secret-key-here
   CORS_ALLOWED_ORIGINS=*
   ```

6. **Deploy!**

---

## After Deployment

Update hardcoded URLs in JavaScript files to your new Render URL:

- `static/js/upload.js` (lines 47, 52)
- `static/js/student_form.js` (lines 33, 162)

Replace: `https://freelance-backend-y0el.onrender.com`  
With: `https://your-new-app.onrender.com`

---

## Testing Locally

```bash
pip install -r requirements.txt
python app.py
```

Visit: `http://localhost:5000`

---

## Need More Details?

See: `../../DEPLOYMENT_GUIDE.md`

---

## FAQ

**Q: Do I need separate frontend/backend deployments?**  
A: No! This is a monolithic Flask app. Deploy this one folder.

**Q: What about Vercel?**  
A: Not needed. Render serves everything (templates + API).

**Q: Where are the templates?**  
A: In this folder → `templates/`

**Q: Where are the static files?**  
A: In this folder → `static/`

**Q: How do I access the app?**  
A: Visit your Render URL → `https://your-app.onrender.com`

