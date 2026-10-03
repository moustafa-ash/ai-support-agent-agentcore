"""Run the six rubric scenarios through deployed agentcore invoke, never fixtures.

Stores raw output privately and sanitized copies in evidence/. These outputs need
semantic review and matching CloudWatch tool evidence before marking scenarios passed.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    ("01-order", "Can you track order ORD-001?", "t1"),
    ("02-refund", "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.", "t2"),
    ("03-rag", "What are the benefits of the Platinum loyalty tier?", "t3"),
    ("04-memory-a", "Hi, I am Jane. I prefer concise responses.", "s-A"),
    ("04-memory-b", "Do you remember my name and communication preference?", "s-B"),
    ("05-discount", "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.", "t5"),
    ("06-browser", "Go to https://www.udacity.com and tell me the page title.", "t6"),
]

def sanitize(text):
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"arn:aws[\w-]*:[^\s\"']+", "[AWS resource ARN redacted]", text)
    text = re.sub(r"\b\d{12}\b", "[account redacted]", text)
    text = re.sub(r"https://[^\s\"']*\.gateway\.bedrock-agentcore\.[^\s\"']+", "[Gateway endpoint redacted]", text)
    text = re.sub(r"\b(?:ASIA|AKIA)[A-Z0-9]{16}\b", "[AWS key redacted]", text)
    text = re.sub(r"https?://[^\s\"']*\.amazonaws\.com[^\s\"']*", "[AWS endpoint redacted]", text)
    text = re.sub(r"ai_support_agent-[A-Za-z0-9]+", "[Runtime ID redacted]", text)
    settings = ROOT / "starter/runtime_settings.json"
    if settings.exists():
        for key, value in json.loads(settings.read_text()).items():
            if key in {"GATEWAY_URL", "KB_ID", "MEMORY_ID"} and value:
                text = text.replace(value, f"[{key} redacted]")
    return text

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=[s[0] for s in SCENARIOS])
    parser.add_argument("--session-suffix", default="")
    args = parser.parse_args()
    private = ROOT / "private/live"
    public = ROOT / "evidence"
    private.mkdir(parents=True, exist_ok=True)
    public.mkdir(exist_ok=True)
    for name, prompt, session in SCENARIOS:
        if args.only and name not in args.only:
            continue
        if name == "04-memory-b":
            # Extraction is asynchronous; the sandbox took about 63 seconds.
            time.sleep(90)
        session += args.session_suffix
        payload = dict(prompt=prompt, customer_id="CUST-123", session_id=session)
        print("Running " + name, flush=True)
        result = subprocess.run(["agentcore", "invoke", json.dumps(payload)], cwd=ROOT / "starter",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
        text = "Payload: " + json.dumps(payload) + f"\nCLI exit code: {result.returncode}\n" + result.stdout
        (private / (name + ".txt")).write_text(text)
        (public / (name + ".txt")).write_text(sanitize(text))
        print(name + " cli_exit=" + str(result.returncode), flush=True)
        if result.returncode:
            raise RuntimeError("Scenario failed; inspect private output before retrying")
    print("LIVE_OUTPUTS_COLLECTED_REVIEW_REQUIRED", flush=True)

if __name__ == "__main__":
    main()
