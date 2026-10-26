import json
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials


def load_local_env():
    env_file = Path(__file__).with_name(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() and not name.lstrip().startswith("#"):
                os.environ.setdefault(name.strip(), value.strip())


load_local_env()
app = FastAPI(title="SiteSaarthi", docs_url=None, redoc_url=None, openapi_url=None)
security = HTTPBasic(auto_error=False)
MAX_AUDIO_BYTES = 4 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    ".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".opus", ".flac", ".webm", ".aac"
}


def require_access(credentials: HTTPBasicCredentials | None = Depends(security)):
    password = os.getenv("SITE_SAARTHI_PASSWORD")
    if not password:
        if os.getenv("VERCEL") or os.getenv("VERCEL_URL"):
            raise HTTPException(503, "Set SITE_SAARTHI_PASSWORD in Vercel project settings.")
        return
    valid = credentials and credentials.username == "site" and secrets.compare_digest(
        credentials.password, password
    )
    if not valid:
        raise HTTPException(
            401,
            "Sign in to SiteSaarthi.",
            headers={"WWW-Authenticate": 'Basic realm="SiteSaarthi"'},
        )


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_access)])
def home():
    return HTMLResponse(PAGE)


@app.post("/api/site-update", dependencies=[Depends(require_access)])
def analyze_site_update(audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(415, "Upload a WAV, MP3, M4A, OGG, FLAC, WEBM, or AAC audio file.")
    audio.file.seek(0, 2)
    size = audio.file.tell()
    audio.file.seek(0)
    if size > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio must be 4 MB or smaller on Vercel.")

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise HTTPException(503, "SARVAM_API_KEY is not configured.")

    try:
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=api_key)
        transcription = client.speech_to_text.transcribe(
            file=(audio.filename, audio.file, audio.content_type or "application/octet-stream"),
            model="saaras:v4",
            mode="transcribe",
        )
        transcript = transcription.transcript.strip()
        if not transcript:
            raise HTTPException(422, "No speech was detected in that recording.")

        response = client.chat.completions(
            model="sarvam-105b",
            temperature=0,
            max_tokens=900,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You turn construction site voice updates into factual structured reports. "
                        "Use only information explicitly stated in the transcript. Do not infer "
                        "dates, quantities, locations, causes, or commitments. Use null for an "
                        "unknown scalar and [] for an unknown list. Preserve the speaker's "
                        "language for quoted text. Return one JSON object with these keys: "
                        "site_area (string or null), report_date (string or null), "
                        "work_completed (array of strings), quantities (array of objects with "
                        "item, amount, unit; each may be null), materials_or_equipment "
                        "(array of strings), quality_observations (array of strings), "
                        "safety_observations (array of strings), blockers (array of strings), "
                        "follow_up_actions (array of strings), uncertainties (array of strings)."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
        )
        content = response.choices[0].message.content
        report = json.loads(content)
        return {"transcript": transcript, "report": report}
    except HTTPException:
        raise
    except (json.JSONDecodeError, IndexError, AttributeError):
        raise HTTPException(502, "Sarvam returned an unreadable report. Please try again.")
    except Exception:
        raise HTTPException(502, "Sarvam could not process this recording. Please try again.")


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SiteSaarthi · Site intelligence</title>
<style>
:root{color-scheme:light;--ink:#18352f;--muted:#61736d;--line:#dce6e1;--paper:#f5f8f5;--green:#175d48;--lime:#d8f27a}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:940px;margin:auto;padding:52px 24px 80px}.brand{font-size:14px;font-weight:750;letter-spacing:.08em;text-transform:uppercase;color:var(--green)}
h1{font-size:clamp(34px,6vw,58px);line-height:1.04;letter-spacing:-.04em;margin:42px 0 16px;max-width:720px}.intro{color:var(--muted);max-width:650px;font-size:18px}
.panel{background:white;border:1px solid var(--line);border-radius:20px;padding:26px;margin-top:34px;box-shadow:0 12px 36px #18352f0a}.panel h2{font-size:20px;margin:0 0 6px}.hint{color:var(--muted);font-size:14px;margin:0 0 22px}
.drop{border:1px dashed #a9bdb4;border-radius:14px;padding:24px;background:#fbfdfb}.drop input{width:100%;margin:10px 0 16px}button{border:0;border-radius:10px;background:var(--green);color:white;padding:12px 18px;font:inherit;font-weight:700;cursor:pointer}button:disabled{opacity:.55;cursor:wait}
#status{color:var(--muted);min-height:24px;margin-top:14px}#result{display:none;margin-top:20px}.transcript{white-space:pre-wrap;background:#f3f7f4;padding:16px;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f7f4;padding:18px;border-radius:12px}footer{margin-top:32px;color:var(--muted);font-size:13px}
</style>
</head>
<body><main>
<div class="brand">SiteSaarthi <span style="color:#9cac9f">/</span> Site intelligence</div>
<h1>Turn site updates into clear next steps.</h1>
<p class="intro">Upload a short voice note. SiteSaarthi transcribes it and organizes the update into a readable progress report.</p>
<section class="panel">
<h2>Transcribe a site update</h2><p class="hint">Use a recording under 30 seconds and 4 MB. English and supported Indian languages are accepted.</p>
<form id="form" class="drop"><label for="audio"><strong>Choose an audio file</strong></label><input id="audio" name="audio" type="file" accept="audio/*,.m4a,.mp4,.webm" required><button id="submit" type="submit">Create site report</button><div id="status" role="status"></div></form>
<div id="result"><h2>Transcript</h2><p id="transcript" class="transcript"></p><h2>Structured report</h2><pre id="report"></pre></div>
</section><footer>Review generated reports before using them for safety, quality, procurement, or contract decisions.</footer>
</main>
<script>
const form=document.querySelector('#form'),button=document.querySelector('#submit'),status=document.querySelector('#status'),result=document.querySelector('#result');
form.addEventListener('submit',async e=>{e.preventDefault();if(!form.audio.files.length)return;button.disabled=true;status.textContent='Transcribing and organizing the update…';result.style.display='none';const body=new FormData();body.append('audio',form.audio.files[0]);try{const response=await fetch('/api/site-update',{method:'POST',body});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not process this recording.');document.querySelector('#transcript').textContent=data.transcript;document.querySelector('#report').textContent=JSON.stringify(data.report,null,2);result.style.display='block';status.textContent='Report ready.'}catch(error){status.textContent=error.message}finally{button.disabled=false}});
</script></body></html>'''


