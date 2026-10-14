"""Persistence layer: reads and writes tasks.json in the current directory."""
import json
from pathlib import Path

DB = Path("tasks.json")

def load_tasks():
    return json.loads(DB.read_text()) if DB.exists() else []

def save_tasks(tasks):
    DB.write_text(json.dumps(tasks, indent=2))
