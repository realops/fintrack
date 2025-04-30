from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import psutil
import os
import logging
import socket
import sys
from logging.handlers import RotatingFileHandler
from config import get_system_info
from collections import defaultdict
from sqlalchemy import func
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transactions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security configurations
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize security extensions
csrf = CSRFProtect(app)
talisman = Talisman(
    app,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
    }
)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/fintrack.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('FinTrack startup')

db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def __init__(self, **kwargs):
        super(Transaction, self).__init__(**kwargs)
        if self.date is None:
            self.date = datetime.utcnow()

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    
    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
    net_balance = total_income - total_expenses
    
    # Log dashboard access
    app.logger.info(f'Dashboard accessed - Income: ₹{total_income:.2f}, Expenses: ₹{total_expenses:.2f}, Balance: ₹{net_balance:.2f}')
    
    return render_template('dashboard.html', 
                         transactions=transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_balance=net_balance,
                         system_info=get_system_info())

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            description = request.form['description']
            category = request.form['category']
            amount = float(request.form['amount'])
            
            # For expenses, ensure the amount is negative
            if category != 'Income' and amount > 0:
                amount = -amount
            
            # Secure transaction creation using SQLAlchemy ORM
            transaction = Transaction(
                description=description,
                category=category,
                amount=amount
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            app.logger.info(f'Transaction added - Description: {description}, Category: {category}, Amount: ₹{amount:.2f}')
            flash('Transaction added successfully!')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to add transaction: {str(e)}')
            flash('Error adding transaction. Please try again.')
        
        return redirect(url_for('dashboard'))
    
    return render_template('add_transaction.html')

@app.route('/report')
def report():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    
    # Calculate category distribution
    category_totals = defaultdict(float)
    for t in transactions:
        category_totals[t.category] += abs(t.amount)
    
    categories = list(category_totals.keys())
    category_amounts = [category_totals[cat] for cat in categories]
    
    # Calculate monthly summary
    monthly_data = defaultdict(lambda: {'income': 0, 'expenses': 0})
    for t in transactions:
        month_key = t.date.strftime('%Y-%m')
        if t.amount > 0:
            monthly_data[month_key]['income'] += t.amount
        else:
            monthly_data[month_key]['expenses'] += abs(t.amount)
    
    # Sort months and prepare data for chart
    months = sorted(monthly_data.keys())
    monthly_income = [monthly_data[month]['income'] for month in months]
    monthly_expenses = [monthly_data[month]['expenses'] for month in months]
    
    app.logger.info('Report generated')
    
    return render_template('report.html', 
                         transactions=transactions,
                         categories=categories,
                         category_amounts=category_amounts,
                         months=months,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses)

@app.route('/sysinfo')
def sysinfo():
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Secure hostname retrieval
    hostname = socket.gethostname()
    
    app.logger.info(f'System info accessed - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%')
    
    return render_template('sysinfo.html',
                         cpu_percent=cpu_percent,
                         memory=memory,
                         disk=disk,
                         hostname=hostname)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Binding to 0.0.0.0 is necessary for container environments
    # to allow external connections to the container
    # This is safe as the container runtime/orchestrator handles the actual network security
    app.run(host='0.0.0.0', port=5001, debug=False)  # nosec B104 