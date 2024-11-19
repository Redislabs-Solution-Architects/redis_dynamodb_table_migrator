FROM python:3.12-slim
LABEL authors="gabriel.cerioni@redis.com"

# Set working directory
WORKDIR /app

# Copy the Python requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Default command to run the migrator script
CMD ["python", "main.py"]