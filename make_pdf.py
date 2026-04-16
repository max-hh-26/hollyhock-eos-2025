#!/usr/bin/env python3
"""Generate EoS-Report-2025.pdf from EoS Report PDF.html using Chrome headless."""

import subprocess
import os
import sys

eos_dir = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(eos_dir, 'EoS Report PDF.html')
pdf_path  = os.path.join(eos_dir, 'EoS-Report-2025.pdf')

chrome_paths = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
]
chrome = next((p for p in chrome_paths if os.path.exists(p)), None)
if not chrome:
    sys.exit('Chrome not found.')

file_url = 'file:///' + html_path.replace('\\', '/')

result = subprocess.run([
    chrome,
    '--headless=new',
    '--disable-gpu',
    f'--print-to-pdf={pdf_path}',
    '--print-to-pdf-no-header',
    '--no-margins',
    '--run-all-compositor-stages-before-draw',
    '--virtual-time-budget=8000',
    file_url,
], capture_output=True, text=True)

if result.returncode == 0 and os.path.exists(pdf_path):
    size_kb = os.path.getsize(pdf_path) // 1024
    print(f'Generated EoS-Report-2025.pdf ({size_kb} KB)')
else:
    print('Chrome stderr:', result.stderr[:500])
    sys.exit('PDF generation failed.')
