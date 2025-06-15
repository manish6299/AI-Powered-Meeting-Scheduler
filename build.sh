#!/usr/bin/env bash

# Step 1: Update apt and install portaudio
apt-get update
apt-get install -y portaudio19-dev

# Step 2: Install Python dependencies
pip install -r requirements.txt
