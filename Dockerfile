FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create directory for SQLite volume
RUN mkdir -p /app/data

# Run the FastHTML app (main.py calls serve())
CMD ["python", "main.py"]
