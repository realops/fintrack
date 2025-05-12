
#!/bin/bash

# Update and install required packages
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

# Create a directory for the application
cd /home/ubuntu
sudo mkdir -p fintrack
sudo chown ubuntu:ubuntu fintrack
cd fintrack

# Clone the repository
git clone https://github.com/shivamadala/fintrack.git

# Create a virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install application dependencies
pip install -r requirements.txt

# Start the Flask app using Gunicorn
gunicorn app:app --bind 0.0.0.0:5001 --workers 4 --daemon