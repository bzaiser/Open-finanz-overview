FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV RUNNING_IN_DOCKER 1

# Create a non-root user early to maximize caching
RUN addgroup --system app && adduser --system --group app

# Set work directory
WORKDIR /app

# Ensure the persistent data and static directories exist
RUN mkdir -p /app/data /app/staticfiles && chown -R app:app /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy python code (only this and below runs on code change)
COPY --chown=app:app . /app/

# Switch to the non-root user
USER app

# Compile translations
RUN python3 manage.py compilemessages

# Collect static files with proper permissions
RUN python3 manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--reload"]
