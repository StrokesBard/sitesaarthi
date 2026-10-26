import os
import sys
from pathlib import Path

# Load the local .env into the process environment without an extra dependency.
env_file = Path(__file__).with_name(".env")
for line in env_file.read_text(encoding="utf-8").splitlines():
    name, separator, value = line.partition("=")
    if separator and name.strip() and not name.lstrip().startswith("#"):
        os.environ.setdefault(name.strip(), value.strip())

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("Set SARVAM_API_KEY in the environment or .env file.")
if len(sys.argv) != 2:
    raise SystemExit("Usage: python transcribe.py <audio-file>")

def main():
    from sarvamai import SarvamAI

    client = SarvamAI(api_subscription_key=api_key)
    with open(sys.argv[1], "rb") as audio:
        result = client.speech_to_text.transcribe(
            file=audio,
            model="saaras:v4",
            mode="transcribe",
        )
    print(result.transcript)

if __name__ == "__main__":
    main()
