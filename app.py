from flask import Flask, render_template
from upload.routes import upload_bp
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(upload_bp)

@app.route("/dashboard")
def dashboard():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template("dashboard.html", files=files)

if __name__ == "__main__":
    app.run(debug=True)
