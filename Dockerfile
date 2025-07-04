# Use an official Python image as base
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /FantasySgpSystem

ENV RUNNING_IN_DOCKER=true

# Install dependencies for Chrome & Selenium
# Chrome + ChromeDriver setup
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gnupg ca-certificates fonts-liberation \
    libappindicator3-1 libasound2 libgbm-dev libgtk-3-0 \
    libnss3 lsb-release xdg-utils jq \
 && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install \
 && rm google-chrome-stable_current_amd64.deb

# Match ChromeDriver to installed Chrome
RUN bash -c '\
  set -e; \
  CHROME_VERSION=$(google-chrome --version | grep -oP "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"); \
  echo "Detected Chrome version: $CHROME_VERSION"; \
  DRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
    | jq -r ".channels.Stable.downloads.chromedriver[] | select(.platform == \"linux64\") | .url"); \
  echo "Resolved ChromeDriver download URL: $DRIVER_URL"; \
  curl -sSL "$DRIVER_URL" -o chromedriver.zip; \
  unzip chromedriver.zip; \
  mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver; \
  chmod +x /usr/local/bin/chromedriver; \
  rm -rf chromedriver.zip chromedriver-linux64; \
  apt-get clean; \
  rm -rf /var/lib/apt/lists/* \
'

    
# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY chrome_profile /chrome_profile

# Copy the rest of the app code into the container
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

RUN mkdir -p /downloads

COPY inseason_entrypoint.sh /inseason_entrypoint.sh
RUN chmod +x /inseason_entrypoint.sh

ENTRYPOINT ["/inseason_entrypoint.sh"]

