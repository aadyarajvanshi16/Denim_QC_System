# Denim QC System

Flask-based industrial denim quality inspection platform — fabric colour
comparison (ΔE / L·a·b), dye recipe extraction, and live RTSP camera-based
quality checks.

## Project structure

```
denim_qc/
├── app.py              # App factory: creates the Flask app, wires up extensions & blueprints
├── wsgi.py              # Production entrypoint (waitress)
├── config.py             # Environment-driven configuration
├── extensions.py          # Shared db / login_manager / csrf instances
├── models.py             # SQLAlchemy models: User, Inspection, RecipeExtraction, AppSetting
├── decorators.py           # @admin_required / @permission_required
├── blueprints/
│   ├── auth.py             # Login / logout
│   ├── dashboard.py         # Home page, inspection history (admin)
│   ├── inspection.py         # Fabric comparison + recipe extraction flows
│   ├── api.py              # Live camera streaming, RTSP connect, live analyze
│   ├── admin.py             # User management, QC threshold settings
│   └── reports.py           # PDF report generation / download / rename / delete
├── pipeline/
│   └── stream_reader.py       # Background-threaded RTSP/webcam frame reader
├── utils/                  # Colour analysis, ROI cropping, chart & PDF generation
├── templates/
└── static/
```

## Setup

1. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   A `.env` is already included for local development. For any other machine,
   copy the example and fill in your own values:
   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY
   ```

3. **Create the first admin account**
   ```bash
   flask --app app create-admin
   ```
   You'll be prompted for a username and password.

4. **Run the app (development)**
   ```bash
   python app.py
   ```
   or with the Flask CLI:
   ```bash
   flask --app app run --debug
   ```

5. **Run the app (production)**
   ```bash
   waitress-serve --host=0.0.0.0 --port=8000 wsgi:app
   ```

## Notes

- The SQLite database, uploaded images, generated results, and saved PDF
  reports are all created automatically on first run and are **not** committed
  to git (see `.gitignore`) — they're per-environment runtime data.
- Admins can grant per-user access to individual features (fabric comparison,
  live quality, recipe extraction, AI reports) and tune the ΔE pass/acceptable
  thresholds from the Admin panel.
- Live quality checks connect to a camera via `/set_rtsp` (an RTSP URL) or
  fall back to the local webcam — see `pipeline/stream_reader.py`.
