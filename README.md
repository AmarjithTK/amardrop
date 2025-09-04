# Amar Drop - Secure File Drop App

A FastAPI-based file drop app with password-only login, custom URL slugs, expiry, multi-file upload, and strong security.

## Features

- Password-only login (no usernames)
- Multi-file upload (drag & drop, max 10 files per upload)
- Custom URL slug for download page
- Expiry (max 7 days)
- Max total upload size: 50MB
- Only safe file types allowed (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.txt`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`)
- Automatic cleanup of expired files
- Secure password (bcrypt hash, set via environment variable)
- Secure HTTP headers
- Directory traversal protection

## Quick Start (Local)

```bash
pip install -r requirements.txt
export AMARDROP_PASSWORD="yourStrongPassword"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit [http://localhost:8000](http://localhost:8000)

---

## Docker Build & Run

1. **Create a Dockerfile**:

    ```dockerfile
    # Use official Python image
    FROM python:3.12-slim

    WORKDIR /app

    # Install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy app code
    COPY . .

    # Expose port
    EXPOSE 8000

    # Set environment variable for password
    ENV AMARDROP_PASSWORD=yourStrongPassword

    # Run the app
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

2. **Build the Docker image**:

    ```bash
    docker build -t amardrop .
    ```

3. **Run the container**:

    ```bash
    docker run -d -p 8000:8000 --name amardrop -e AMARDROP_PASSWORD=yourStrongPassword amardrop
    ```

---

## Deploying Widescale

- Use a cloud provider (Azure, AWS, GCP) or a VPS.
- Use Docker Compose or Kubernetes for scaling.
- Use a reverse proxy (nginx, traefik) for HTTPS and domain routing.
- Set environment variables for secrets (e.g., password).
- Persist the `uploads` and `files.db` volumes for durability.

Example Docker Compose snippet:

```yaml
version: '3'
services:
  amardrop:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./files.db:/app/files.db
    environment:
      - AMARDROP_PASSWORD=yourStrongPassword
```

---

## Security Notes

- **Change the password before deploying** (`AMARDROP_PASSWORD`).
- Only safe file types are allowed.
- Directory traversal is prevented.
- Secure HTTP headers are set.
- Use HTTPS in production.
- Limit access to trusted users if needed.
- Review and monitor server logs for anomalies.

---

## License

MIT
