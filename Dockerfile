# Use an official Python image as base
FROM python:3.12

# Set the working directory inside the container
WORKDIR /FantasySgpSystem

# Install dependencies for Chrome & Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libgbm-dev \
    libgtk-3-0 \
    libnss3 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install

# Install ChromeDriver (ensure version compatibility with Chrome)
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver
    
# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code into the container
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

COPY inseason_entrypoint.sh /inseason_entrypoint.sh
RUN chmod +x /inseason_entrypoint.sh

ENTRYPOINT ["/inseason_entrypoint.sh"]

# Optional: keep Flask exposed
EXPOSE 5000
