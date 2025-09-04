# Amar Drop - Secure File Drop App

A FastAPI-based file drop app with password-only login, custom URL slugs, expiry, and multi-file upload.

## Features

- Password-only login (no usernames)
- Multi-file upload (drag & drop)
- Custom URL slug for download page
- Expiry (max 7 days)
- Max total upload size: 50MB
- Automatic cleanup of expired files

## Quick Start (Local)

```bash
pip install fastapi uvicorn jinja2
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit [http://localhost:8000](http://localhost:8000)

---

## Docker Build & Run

1. **Create a Dockerfile** (example below):

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

    # Run the app
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

2. **Create requirements.txt**:

    ```
    fastapi
    uvicorn
    jinja2
    ```

3. **Build the Docker image**:

    ```bash
    docker build -t amardrop .
    ```

4. **Run the container**:

    ```bash
    docker run -d -p 8000:8000 --name amardrop amardrop
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
      - PASSWORD=yourpassword
```

---

## Security Notes

- Change the password before deploying.
- Use HTTPS in production.
- Limit access to trusted users if needed.

---

## License

MIT
