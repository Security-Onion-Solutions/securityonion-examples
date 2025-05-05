FROM python:3.13-slim

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src/app.py

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
