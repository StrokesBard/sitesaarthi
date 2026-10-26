# SiteSaarthi MVP

This first deployable slice handles one workflow: upload a short site voice update, transcribe it with Sarvam Saaras v4, and structure the transcript into a progress report with Sarvam-105B.

## Local run

1. Create and activate a Python 3.12 virtual environment.
2. Install the runtime packages: `pip install -r requirements.txt`.
3. Set `SARVAM_API_KEY` in `.env` or the process environment.
4. Start the app: `uvicorn app:app --reload`.
5. Open `http://127.0.0.1:8000`.

Audio is limited to 30 seconds and 4 MB for compatibility with Vercel Function request limits.

## Deploy to Vercel

Deploy this `Sarvam Session` directory as the Vercel project root. Vercel detects the FastAPI app in `app.py` and installs `requirements.txt` automatically.

In Vercel Project Settings → Environment Variables, add:

- `SARVAM_API_KEY` — your Sarvam subscription key
- `SITE_SAARTHI_PASSWORD` — a private password for the app's HTTP Basic login (username: `site`)

Set both for Production (and Preview if you plan to use Preview deployments). Do not commit `.env`; it is excluded from Git and Vercel uploads.

## Current scope

This MVP covers voice transcription and report structuring. BOQ/drawing extraction, construction-photo analysis, schedule comparison, persistent project data, and agent follow-up workflows still need to be built before SiteSaarthi is the full platform described in the project brief.
