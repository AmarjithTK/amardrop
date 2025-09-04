from flask import Blueprint, render_template, request, redirect, url_for, current_app
import os

upload_bp = Blueprint('upload', __name__)

@upload_bp.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        files = request.files.getlist("files")
        saved_files = []
        upload_folder = current_app.config['UPLOAD_FOLDER']
        for file in files:
            if file.filename:
                filepath = os.path.join(upload_folder, file.filename)
                file.save(filepath)
                saved_files.append(file.filename)
        return redirect(url_for('dashboard'))
    return render_template("upload.html", files=[])
