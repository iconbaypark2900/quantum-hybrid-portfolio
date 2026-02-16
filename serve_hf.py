"""
Hugging Face Spaces server: serves the Flask API + built React frontend from a single process.
Use this when deploying to HF Spaces (sdk: docker, app_port: 7860).
"""
import os

os.environ["HF_SPACES"] = "1"
os.environ.setdefault("CORS_ORIGINS", "*")

from flask import send_from_directory

# Import the Flask app from api (API routes registered first)
from api import app

BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "build")

# Point Flask's built-in static handler to the React build's static assets.
# Without this, Flask intercepts /static/* requests and looks in the wrong folder.
app.static_folder = os.path.join(BUILD_DIR, "static")
app.static_url_path = "/static"


@app.route("/", methods=["GET"])
def index():
    """Serve React app root."""
    if not os.path.isdir(BUILD_DIR):
        return "<pre>Frontend build not found. BUILD_DIR=%s</pre>" % BUILD_DIR, 503
    return send_from_directory(BUILD_DIR, "index.html")


@app.route("/<path:path>", methods=["GET"])
def catch_all(path):
    """Serve React files. API routes (/api/*, /metrics) and /static/* take precedence."""
    if not os.path.isdir(BUILD_DIR):
        return "<pre>Frontend build not found. BUILD_DIR=%s</pre>" % BUILD_DIR, 503
    file_path = os.path.join(BUILD_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(BUILD_DIR, path)
    return send_from_directory(BUILD_DIR, "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    app.run(host="0.0.0.0", port=port, debug=False)
