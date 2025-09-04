from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
import os

upload_bp = Blueprint('upload', __name__)

@upload_bp.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        upload_folder = current_app.config['UPLOAD_FOLDER']
        saved_files = []
        # Handle both single and multiple file uploads
        if 'files' in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file.filename:
                    filepath = os.path.join(upload_folder, file.filename)
                    file.save(filepath)
                    saved_files.append(file.filename)
        # Always return JSON for AJAX (Dropzone)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "files": saved_files})
        return redirect(url_for('dashboard'))
    return render_template("upload.html", files=[])
