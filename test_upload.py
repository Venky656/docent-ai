#!/usr/bin/env python3
"""Test upload endpoint"""
import requests

# Test if server is running
try:
    response = requests.get("http://127.0.0.1:5000/health", timeout=5)
    print(f"✓ Server is running: {response.json()}")
except Exception as e:
    print(f"✗ Server not running: {e}")
    print("\nStart the server first: python app.py")
    exit(1)

# Test upload
print("\nTesting upload...")
print("Make sure you have a test.pdf file in the same directory")

import os
if not os.path.exists("test.pdf"):
    print("Creating dummy PDF for test...")
    from reportlab.pdfgen import canvas
    c = canvas.Canvas("test.pdf")
    c.drawString(100, 750, "Test PDF Document")
    c.save()
    print("✓ Created test.pdf")

files = {'file': open('test.pdf', 'rb')}
response = requests.post("http://127.0.0.1:5000/upload", files=files, timeout=30)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
