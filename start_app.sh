#!/bin/bash
# Simple script to start the PDF search app with correct architecture

cd "$(dirname "$0")"
arch -arm64 python3 app.py

