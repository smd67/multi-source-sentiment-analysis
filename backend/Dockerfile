# Use an official Python runtime as a parent image
FROM python:3.9

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libatk-bridge2.0-0 \
        libdrm2 \
        libatspi2.0-0 \
        libgbm1 \
        libasound2 \
        libnspr4 \
        libnss3 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libxkbcommon0 \ 
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
RUN pip install poetry

COPY pyproject.toml poetry.lock src/download.py ./

RUN poetry install --no-root

RUN poetry run playwright install chromium

RUN poetry run python download.py

COPY . /app

# Expose the port your application listens on (if applicable)
EXPOSE 8005

ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Define the command to run your application
CMD ["poetry", "run", "uvicorn", "src.endpoint:app", "--host", "0.0.0.0", "--reload"]