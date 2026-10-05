import sys
for mod in ["openai", "chromadb", "requests", "bs4", "urllib", "sqlite3"]:
    try:
        __import__(mod)
        print(f"Module {mod}: AVAILABLE")
    except ImportError as e:
        print(f"Module {mod}: NOT AVAILABLE ({e})")
