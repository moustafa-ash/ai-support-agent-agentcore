"""Display an actual saved CLI transcript for readable terminal screenshots.

Does not invoke AWS, generate responses, or change evidence. Full sanitized
CLI output remains in the input file; only the toolkit metadata box is omitted.
"""
import argparse
from pathlib import Path
import textwrap

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("transcript", type=Path)
args = parser.parse_args()
text = args.transcript.read_text()
print("Recorded deployed AgentCore CLI invocation (actual output)")
for line in text.splitlines():
    if line.startswith(("Captured UTC:", "$ agentcore invoke", "Intentional outage:")):
        print(textwrap.fill(line, width=100, subsequent_indent="  "))
if "Response:" not in text:
    raise ValueError("Transcript has no CLI response; cannot use as deployment evidence")
print()
for line in text.split("Response:", 1)[1].strip().splitlines():
    print(textwrap.fill(line, width=100))
