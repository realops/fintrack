from app import app, db, Transaction
from datetime import datetime

def test_transaction_model(app):
    """Test basic transaction model"""
    with app.app_context():
        # Create a test transaction
        transaction = Transaction(
            description="Test Transaction",
            category="Test",
            amount=100.00
        )
        
        # Test the model attributes
        assert transaction.description == "Test Transaction"
        assert transaction.category == "Test"
        assert transaction.amount == 100.00
        assert transaction.date is not None
        assert isinstance(transaction.date, datetime)

def test_transaction_creation(app):
    """Test basic transaction creation"""
    with app.app_context():
        transaction = Transaction(
            description="Test Transaction",
            category="Test",
            amount=100.00
        )
        
        assert transaction.description == "Test Transaction"
        assert transaction.category == "Test"
        assert transaction.amount == 100.00
        assert transaction.date is not None
        assert isinstance(transaction.date, datetime)

def test_transaction_income(app):
    """Test income transaction"""
    with app.app_context():
        transaction = Transaction(
            description="Salary",
            category="Income",
            amount=50000.00
        )
        
        assert transaction.amount > 0
        assert transaction.category == "Income"
        assert transaction.date is not None
        assert isinstance(transaction.date, datetime)

def test_transaction_expense(app):
    """Test expense transaction"""
    with app.app_context():
        transaction = Transaction(
            description="Groceries",
            category="Food",
            amount=-2000.00
        )
        
        assert transaction.amount < 0
        assert transaction.category == "Food"
        assert transaction.date is not None
        assert isinstance(transaction.date, datetime)

def test_transaction_date_default(app):
    """Test that date is automatically set"""
    with app.app_context():
        transaction = Transaction(
            description="Test",
            category="Test",
            amount=100.00
        )
        
        assert transaction.date is not None
        assert isinstance(transaction.date, datetime)
        # Test that the date is recent (within the last minute)
        assert (datetime.utcnow() - transaction.date).total_seconds() < 60 