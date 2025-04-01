FROM python:3.11-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    inkscape

RUN apt-get update

# Create python venv
RUN python -m venv /opt/venv

# Adding python venv to PATH
ENV PATH="/opt/venv/bin:${PATH}"

# Copying over files and changing working directory
COPY . /root/DiplomacyGM/
WORKDIR /root/DiplomacyGM

# Updating pip and installing python requirements
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

# Copying Fonts from assets if they exist, these are needed for words on maps to look nice
RUN [ -e ./assets/fonts/TTF ]  &&  mv ./assets/fonts/TTF /usr/share/fonts/TTF || echo 0

ENTRYPOINT ["python3"]
CMD ["main.py"]
