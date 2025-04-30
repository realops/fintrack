from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import psutil
import os
import logging
from logging.handlers import RotatingFileHandler
from config import get_system_info
from collections import defaultdict
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transactions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        description = request.form['description']
        category = request.form['category']
        amount = float(request.form['amount'])
        
        # For expenses, ensure the amount is negative
        if category != 'Income' and amount > 0:
            amount = -amount
        
        transaction = Transaction(
            description=description,
            category=category,
            amount=amount
        )
        
        try:
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
    
    app.logger.info(f'System info accessed - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%')
    
    return render_template('sysinfo.html',
                         cpu_percent=cpu_percent,
                         memory=memory,
                         disk=disk)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 