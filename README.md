# JANOVA

Assistant IA local orienté orchestration (Windows-first) avec Ollama, UI desktop Tkinter, agents arrière-plan et modules dynamiques.

## Lancer

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python janova_desktop.py
# ou
python janova_app.py
```

## Build exécutable (Windows)

```bash
pip install pyinstaller
pyinstaller --name JANOVA --onefile --noconsole janova_app.py
```
