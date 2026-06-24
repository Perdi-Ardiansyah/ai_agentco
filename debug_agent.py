import sys
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)  # pyrefly: ignore[missing-attribute]
import langchain.globals  # pyrefly: ignore[missing-import]
langchain.globals.set_debug(True)
from agent import run_agent

print("Running...")
print(run_agent())
