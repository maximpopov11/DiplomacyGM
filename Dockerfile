FROM python:3.13-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl

RUN apt-get update

# Install rust
RUN curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh -s -- -y

# Create python venv
RUN python -m venv /opt/venv

# Adding python venv and cargo ot PATH
ENV PATH="/opt/venv/bin:/root/.cargo/bin:${PATH}"

# Copying over files and changing working directory
COPY . /root/DiplomacyGM/
WORKDIR /root/DiplomacyGM

# Updating pip and installing python requirements
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt


ENTRYPOINT ["python3"]
CMD ["main.py"]
