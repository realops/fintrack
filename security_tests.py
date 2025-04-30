import pytest
from app import app, db
import os
import re
from flask import url_for
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Configure security logging
if not os.path.exists('logs/security'):
    os.makedirs('logs/security')
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('logs/security/security_scan.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
security_logger.addHandler(file_handler)

def log_security_issue(issue_type, description, severity='MEDIUM'):
    """Log security issues with timestamp and severity"""
    security_logger.warning(f"[{severity}] {issue_type}: {description}")

def test_sql_injection_protection(app, client):
    """Test SQL injection protection"""
    with app.app_context():
        # Test SQL injection attempts
        injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE transactions; --",
            "' UNION SELECT * FROM users; --"
        ]
        
        for attempt in injection_attempts:
            response = client.post('/add', data={
                'description': attempt,
                'category': 'Test',
                'amount': '100'
            })
            assert response.status_code == 200
            assert b'Error' not in response.data
            log_security_issue('SQL Injection', f'Attempted injection: {attempt}')

def test_xss_protection(app, client):
    """Test XSS protection"""
    with app.app_context():
        # Test XSS attempts
        xss_attempts = [
            '<script>alert("xss")</script>',
            '<img src="x" onerror="alert(1)">',
            'javascript:alert(1)'
        ]
        
        for attempt in xss_attempts:
            response = client.post('/add', data={
                'description': attempt,
                'category': 'Test',
                'amount': '100'
            })
            assert response.status_code == 200
            assert b'<script>' not in response.data
            log_security_issue('XSS', f'Attempted XSS: {attempt}')

def test_csrf_protection(app, client):
    """Test CSRF protection"""
    with app.app_context():
        # Test without CSRF token
        response = client.post('/add', data={
            'description': 'Test',
            'category': 'Test',
            'amount': '100'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Error' in response.data
        log_security_issue('CSRF', 'CSRF token validation failed')

def test_password_policy(app):
    """Test password policy enforcement"""
    weak_passwords = [
        'password',
        '123456',
        'qwerty',
        'admin123'
    ]
    
    for password in weak_passwords:
        assert len(password) >= 8, f"Weak password detected: {password}"
        assert re.search(r'[A-Z]', password), f"Password missing uppercase: {password}"
        assert re.search(r'[a-z]', password), f"Password missing lowercase: {password}"
        assert re.search(r'[0-9]', password), f"Password missing number: {password}"
        assert re.search(r'[!@#$%^&*(),.?":{}|<>]', password), f"Password missing special char: {password}"
        log_security_issue('Password Policy', f'Weak password detected: {password}')

def test_security_headers(app, client):
    """Test security headers"""
    with app.app_context():
        response = client.get('/')
        headers = response.headers
        
        # Check for essential security headers
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert 'Content-Security-Policy' in headers
        log_security_issue('Security Headers', 'Missing security headers')

def test_input_validation(app, client):
    """Test input validation"""
    with app.app_context():
        # Test invalid inputs
        invalid_inputs = [
            {'amount': 'not_a_number'},
            {'amount': '-1000000'},  # Extremely large negative number
            {'amount': '1000000'},   # Extremely large positive number
            {'description': 'a' * 201},  # Too long description
            {'category': 'a' * 51}   # Too long category
        ]
        
        for invalid in invalid_inputs:
            response = client.post('/add', data=invalid)
            assert response.status_code == 200
            assert b'Error' in response.data
            log_security_issue('Input Validation', f'Invalid input detected: {invalid}')

def test_session_security(app, client):
    """Test session security"""
    with app.app_context():
        # Test session cookie settings
        response = client.get('/')
        cookies = response.headers.getlist('Set-Cookie')
        
        for cookie in cookies:
            assert 'HttpOnly' in cookie
            assert 'Secure' in cookie
            assert 'SameSite' in cookie
        log_security_issue('Session Security', 'Insecure session cookie settings')

def test_error_handling(app, client):
    """Test error handling and information disclosure"""
    with app.app_context():
        # Test error pages
        response = client.get('/nonexistent')
        assert response.status_code == 404
        assert b'stack trace' not in response.data.lower()
        assert b'debug' not in response.data.lower()
        log_security_issue('Error Handling', 'Sensitive information disclosure in error pages')

def test_file_upload_security(app, client):
    """Test file upload security"""
    with app.app_context():
        # Test file upload restrictions
        malicious_files = [
            ('test.php', '<?php system($_GET["cmd"]); ?>'),
            ('test.exe', 'MZ...'),
            ('test.sh', '#!/bin/bash\nrm -rf /')
        ]
        
        for filename, content in malicious_files:
            response = client.post('/add', data={
                'file': (content, filename)
            })
            assert response.status_code == 200
            assert b'Error' in response.data
            log_security_issue('File Upload', f'Malicious file upload attempt: {filename}')

def test_rate_limiting(app, client):
    """Test rate limiting"""
    with app.app_context():
        # Test multiple rapid requests
        for _ in range(100):
            response = client.get('/')
            if response.status_code == 429:
                break
        assert response.status_code == 429
        log_security_issue('Rate Limiting', 'Rate limiting not properly enforced') 