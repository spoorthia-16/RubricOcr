from flask import Flask
from flask_cors import CORS

from routes.upload import upload_bp

app = Flask(__name__)

CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

app.register_blueprint(upload_bp)

@app.route("/")
def home():
    return {
        "message": "Rubric OCR Backend Running"
    }

if __name__ == "__main__":
    app.run(port=5001, debug=True)