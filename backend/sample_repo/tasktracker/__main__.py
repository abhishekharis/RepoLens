"""Entry point: `python -m tasktracker` parses CLI arguments and dispatches to storage functions."""
import sys
from .storage import load_tasks, save_tasks

def main(argv):
    tasks = load_tasks()
    cmd = argv[0] if argv else "list"
    if cmd == "add":
        tasks.append({"title": " ".join(argv[1:]), "done": False})
    elif cmd == "done":
        tasks[int(argv[1]) - 1]["done"] = True
    for i, t in enumerate(tasks, 1):
        print(f"{i}. [{'x' if t['done'] else ' '}] {t['title']}")
    save_tasks(tasks)

if __name__ == "__main__":
    main(sys.argv[1:])
