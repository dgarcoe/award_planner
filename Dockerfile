FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY config.py .
COPY charts.py .
COPY ui_components.py .
COPY admin_functions.py .
COPY database.py .
COPY translations.py .
COPY mobile_styles.py .

# Copy Streamlit config (dark mode)
COPY .streamlit .streamlit

# Create directory for database persistence
RUN mkdir -p /app/data

# Set environment variable for database path
ENV DATABASE_PATH=/app/data/ham_coordinator.db

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
