import json
import os

from Jarvis.config import config


def main():
    path = os.path.abspath(str(getattr(config, "runtime_replay_path", "Jarvis/data/conversation_replay.jsonl")))
    if not os.path.exists(path):
        print("No replay file found.")
        return
    with open(path, "r", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    print(f"Replay events: {len(rows)}")
    for row in rows[-40:]:
        print(f"{row.get('ts')} [{row.get('turn_id')}] {row.get('stage')}: {str(row.get('payload'))[:180]}")


if __name__ == "__main__":
    main()

