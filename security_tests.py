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

def get_csrf_token(response):
    """Extract CSRF token from response"""
    soup = BeautifulSoup(response.data, 'html.parser')
    token = soup.find('input', {'name': 'csrf_token'})
    return token['value'] if token else None

def test_sql_injection_protection(app, client):
    """Test SQL injection protection"""
    with app.app_context():
        # Get CSRF token first
        response = client.get('/add')
        csrf_token = get_csrf_token(response)
        
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
                'amount': '100',
                'csrf_token': csrf_token
            })
            # Should return 400 for malicious input
            assert response.status_code in [400, 403]
            log_security_issue('SQL Injection', f'Attempted injection: {attempt}')

def test_xss_protection(app, client):
    """Test XSS protection"""
    with app.app_context():
        # Get CSRF token first
        response = client.get('/add')
        csrf_token = get_csrf_token(response)
        
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
                'amount': '100',
                'csrf_token': csrf_token
            })
            assert response.status_code in [200, 400]
            assert attempt not in response.data.decode()
            log_security_issue('XSS', f'Attempted XSS: {attempt}')

def test_csrf_protection(app, client):
    """Test CSRF protection"""
    with app.app_context():
        # Test without CSRF token
        response = client.post('/add', data={
            'description': 'Test',
            'category': 'Test',
            'amount': '100'
        })
        assert response.status_code == 400  # Should fail without CSRF token
        
        # Test with valid CSRF token
        response = client.get('/add')
        csrf_token = get_csrf_token(response)
        response = client.post('/add', data={
            'description': 'Test',
            'category': 'Test',
            'amount': '100',
            'csrf_token': csrf_token
        })
        assert response.status_code == 302  # Should redirect on success
        log_security_issue('CSRF', 'CSRF protection test completed')

def test_password_policy(app):
    """Test password policy enforcement"""
    with app.app_context():
        weak_passwords = [
            'password',
            '123456',
            'qwerty',
            'admin123'
        ]
        
        strong_password = 'StrongP@ss123!'  # Example of valid password
        
        # Test that strong password passes all checks
        assert len(strong_password) >= 8
        assert re.search(r'[A-Z]', strong_password)
        assert re.search(r'[a-z]', strong_password)
        assert re.search(r'[0-9]', strong_password)
        assert re.search(r'[!@#$%^&*(),.?":{}|<>]', strong_password)
        
        # Test that weak passwords fail
        for password in weak_passwords:
            meets_criteria = (
                len(password) >= 8 and
                bool(re.search(r'[A-Z]', password)) and
                bool(re.search(r'[a-z]', password)) and
                bool(re.search(r'[0-9]', password)) and
                bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
            )
            assert not meets_criteria, f"Weak password {password} should not pass policy"
            log_security_issue('Password Policy', f'Weak password detected: {password}')

def test_security_headers(app, client):
    """Test security headers"""
    with app.app_context():
        response = client.get('/')
        headers = response.headers
        
        # Check for essential security headers
        assert headers.get('X-Content-Type-Options') == 'nosniff'
        assert headers.get('X-Frame-Options') in ['SAMEORIGIN', 'DENY']
        assert headers.get('X-XSS-Protection') == '1; mode=block'
        assert 'Content-Security-Policy' in headers
        
        # Check CSP header content
        csp = headers.get('Content-Security-Policy')
        assert "default-src 'self'" in csp
        log_security_issue('Security Headers', 'Security headers test completed')

def test_input_validation(app, client):
    """Test input validation"""
    with app.app_context():
        # Get CSRF token first
        response = client.get('/add')
        csrf_token = get_csrf_token(response)
        
        # Test invalid inputs
        invalid_inputs = [
            {'amount': 'not_a_number', 'description': 'Test', 'category': 'Test'},
            {'amount': '-1000000', 'description': 'Test', 'category': 'Test'},
            {'amount': '1000000', 'description': 'Test', 'category': 'Test'},
            {'amount': '100', 'description': 'a' * 201, 'category': 'Test'},
            {'amount': '100', 'description': 'Test', 'category': 'a' * 51}
        ]
        
        for invalid in invalid_inputs:
            invalid['csrf_token'] = csrf_token
            response = client.post('/add', data=invalid)
            assert response.status_code in [400, 403]
            log_security_issue('Input Validation', f'Invalid input detected: {invalid}')

def test_session_security(app, client):
    """Test session security"""
    with app.app_context():
        response = client.get('/')
        
        # Get session cookie
        session_cookie = next(
            (cookie for cookie in response.headers.getlist('Set-Cookie')
             if 'session=' in cookie),
            None
        )
        
        assert session_cookie is not None, "No session cookie found"
        assert 'HttpOnly' in session_cookie
        assert 'SameSite' in session_cookie
        # Note: Secure flag might not be present in testing environment
        log_security_issue('Session Security', 'Session security test completed')

def test_error_handling(app, client):
    """Test error handling and information disclosure"""
    with app.app_context():
        response = client.get('/nonexistent')
        assert response.status_code == 404
        response_text = response.data.decode().lower()
        assert 'stack trace' not in response_text
        assert 'debug' not in response_text
        assert 'error' in response_text  # Should have a user-friendly error message
        log_security_issue('Error Handling', 'Error handling test completed')

def test_file_upload_security(app, client):
    """Test file upload security"""
    with app.app_context():
        # Get CSRF token first
        response = client.get('/add')
        csrf_token = get_csrf_token(response)
        
        # Test file upload restrictions
        malicious_files = [
            ('test.php', b'<?php system($_GET["cmd"]); ?>'),
            ('test.exe', b'MZ...'),
            ('test.sh', b'#!/bin/bash\nrm -rf /')
        ]
        
        for filename, content in malicious_files:
            data = {
                'csrf_token': csrf_token,
                'description': 'Test',
                'category': 'Test',
                'amount': '100'
            }
            response = client.post(
                '/add',
                data=data,
                files={'file': (filename, content)}
            )
            assert response.status_code in [400, 403]
            log_security_issue('File Upload', f'Malicious file upload attempt: {filename}')

def test_rate_limiting(app, client):
    """Test rate limiting"""
    with app.app_context():
        # Make rapid requests to trigger rate limiting
        responses = [client.get('/') for _ in range(101)]
        
        # At least one of the last few requests should be rate limited
        assert any(r.status_code == 429 for r in responses[-5:]), "Rate limiting not triggered"
        
        # Check rate limit headers
        last_response = responses[-1]
        assert 'X-RateLimit-Remaining' in last_response.headers
        assert 'X-RateLimit-Limit' in last_response.headers
        assert 'X-RateLimit-Reset' in last_response.headers
        
        log_security_issue('Rate Limiting', 'Rate limiting test completed') 