from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
from datetime import datetime
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from functools import wraps

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE = 'wallet.db'
COINGECKO_API = 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd'

# Email Configuration (Configure these with your SMTP settings)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_EMAIL = os.getenv('SMTP_EMAIL', 'shanjushreea@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# Initialize Web3 for signature verification
w3 = Web3()

# Database Setup
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT UNIQUE NOT NULL,
        balance REAL DEFAULT 100.0,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_address TEXT NOT NULL,
        to_address TEXT NOT NULL,
        amount REAL NOT NULL,
        eth_price REAL,
        signature TEXT,
        tx_hash TEXT UNIQUE,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (from_address) REFERENCES users(address),
        FOREIGN KEY (to_address) REFERENCES users(address)
    )''')
    
    conn.commit()
    conn.close()

# Database Helper Functions
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def generate_tx_hash():
    return '0x' + secrets.token_hex(32)

# Price Fetching
def get_eth_price():
    """Fetch real-time ETH to USD price from CoinGecko"""
    try:
        response = requests.get(COINGECKO_API, timeout=5)
        data = response.json()
        return data['ethereum']['usd']
    except Exception as e:
        print(f"Error fetching ETH price: {e}")
        return None

def usd_to_eth(usd_amount):
    """Convert USD to ETH"""
    eth_price = get_eth_price()
    if eth_price:
        return usd_amount / eth_price
    return None

# Email Notification
def send_email_notification(to_email, subject, body):
    """Send email notification to user"""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("SMTP credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Signature Verification
def verify_signature(message, signature, address):
    """Verify that the signature matches the address"""
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = w3.eth.account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == address.lower()
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False

# API Endpoints

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    """Create a new wallet"""
    data = request.json
    address = data.get('address')
    email = data.get('email')
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Validate Ethereum address format
    if not w3.is_address(address):
        return jsonify({'error': 'Invalid Ethereum address'}), 400
    
    db = get_db()
    try:
        db.execute('INSERT INTO users (address, email, balance) VALUES (?, ?, ?)',
                   (address.lower(), email, 100.0))
        db.commit()
        
        # Send welcome email
        if email:
            subject = "Welcome to ETH Mock Wallet!"
            body = f"""
            <h2>Welcome to ETH Mock Wallet!</h2>
            <p>Your wallet has been created successfully.</p>
            <p><strong>Address:</strong> {address}</p>
            <p><strong>Starting Balance:</strong> 100 ETH</p>
            <p>You can now start sending and receiving ETH!</p>
            """
            send_email_notification(email, subject, body)
        
        return jsonify({
            'success': True,
            'address': address,
            'balance': 100.0
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Wallet already exists'}), 409
    finally:
        db.close()

@app.route('/api/wallet/<address>/balance', methods=['GET'])
def get_balance(address):
    """Get wallet balance"""
    if not w3.is_address(address):
        return jsonify({'error': 'Invalid Ethereum address'}), 400
    
    db = get_db()
    user = db.execute('SELECT balance FROM users WHERE address = ?',
                      (address.lower(),)).fetchone()
    db.close()
    
    if not user:
        return jsonify({'error': 'Wallet not found'}), 404
    
    eth_price = get_eth_price()
    balance_eth = user['balance']
    balance_usd = balance_eth * eth_price if eth_price else None
    
    return jsonify({
        'address': address,
        'balance_eth': balance_eth,
        'balance_usd': balance_usd,
        'eth_price': eth_price
    })

@app.route('/api/price', methods=['GET'])
def get_price():
    """Get current ETH price"""
    eth_price = get_eth_price()
    if eth_price:
        return jsonify({'eth_usd': eth_price})
    return jsonify({'error': 'Failed to fetch price'}), 503

@app.route('/api/convert', methods=['POST'])
def convert_currency():
    """Convert between USD and ETH"""
    data = request.json
    usd_amount = data.get('usd')
    eth_amount = data.get('eth')
    
    eth_price = get_eth_price()
    if not eth_price:
        return jsonify({'error': 'Failed to fetch ETH price'}), 503
    
    if usd_amount:
        return jsonify({
            'usd': usd_amount,
            'eth': usd_amount / eth_price,
            'eth_price': eth_price
        })
    elif eth_amount:
        return jsonify({
            'eth': eth_amount,
            'usd': eth_amount * eth_price,
            'eth_price': eth_price
        })
    else:
        return jsonify({'error': 'Provide either USD or ETH amount'}), 400

@app.route('/api/transaction/send', methods=['POST'])
def send_transaction():
    """Process a transaction"""
    data = request.json
    from_address = data.get('from')
    to_address = data.get('to')
    amount = data.get('amount')
    amount_type = data.get('amount_type', 'eth')  # 'eth' or 'usd'
    signature = data.get('signature')
    message = data.get('message')
    
    # Validation
    if not all([from_address, to_address, amount, signature, message]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if not w3.is_address(from_address) or not w3.is_address(to_address):
        return jsonify({'error': 'Invalid Ethereum address'}), 400
    
    # Verify signature (skip for mock signatures in testing)
    if signature != '0x_mock_signature_for_testing':
        if not verify_signature(message, signature, from_address):
            return jsonify({'error': 'Invalid signature'}), 401
    
    # Convert USD to ETH if needed
    eth_price = get_eth_price()
    if amount_type == 'usd':
        if not eth_price:
            return jsonify({'error': 'Failed to fetch ETH price'}), 503
        amount_eth = amount / eth_price
    else:
        amount_eth = amount
    
    db = get_db()
    
    try:
        # Check sender balance
        sender = db.execute('SELECT balance, email FROM users WHERE address = ?',
                           (from_address.lower(),)).fetchone()
        
        if not sender:
            return jsonify({'error': 'Sender wallet not found'}), 404
        
        if sender['balance'] < amount_eth:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Check if recipient exists, create if not
        recipient = db.execute('SELECT email FROM users WHERE address = ?',
                              (to_address.lower(),)).fetchone()
        
        if not recipient:
            db.execute('INSERT INTO users (address, balance) VALUES (?, ?)',
                      (to_address.lower(), 0.0))
            db.commit()
            recipient_email = None
        else:
            recipient_email = recipient['email']
        
        # Generate transaction hash
        tx_hash = generate_tx_hash()
        
        # Update balances
        db.execute('UPDATE users SET balance = balance - ? WHERE address = ?',
                   (amount_eth, from_address.lower()))
        db.execute('UPDATE users SET balance = balance + ? WHERE address = ?',
                   (amount_eth, to_address.lower()))
        
        # Record transaction
        db.execute('''INSERT INTO transactions 
                     (from_address, to_address, amount, eth_price, signature, tx_hash, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (from_address.lower(), to_address.lower(), amount_eth, eth_price, signature, tx_hash, 'completed'))
        
        db.commit()
        
        # Send email notifications
        if sender['email']:
            subject = "Transaction Sent"
            body = f"""
            <h2>Transaction Successful</h2>
            <p>You have sent <strong>{amount_eth:.6f} ETH</strong></p>
            <p><strong>To:</strong> {to_address}</p>
            <p><strong>Transaction Hash:</strong> {tx_hash}</p>
            <p><strong>ETH Price:</strong> ${eth_price:.2f}</p>
            """
            send_email_notification(sender['email'], subject, body)
        
        if recipient_email:
            subject = "ETH Received"
            body = f"""
            <h2>You've Received ETH!</h2>
            <p>You have received <strong>{amount_eth:.6f} ETH</strong></p>
            <p><strong>From:</strong> {from_address}</p>
            <p><strong>Transaction Hash:</strong> {tx_hash}</p>
            <p><strong>ETH Price:</strong> ${eth_price:.2f}</p>
            """
            send_email_notification(recipient_email, subject, body)
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash,
            'amount_eth': amount_eth,
            'amount_usd': amount_eth * eth_price if eth_price else None,
            'from': from_address,
            'to': to_address
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Transaction failed: {str(e)}'}), 500
    finally:
        db.close()

@app.route('/api/transactions/<address>', methods=['GET'])
def get_transactions(address):
    """Get transaction history for an address"""
    if not w3.is_address(address):
        return jsonify({'error': 'Invalid Ethereum address'}), 400
    
    db = get_db()
    transactions = db.execute('''
        SELECT * FROM transactions 
        WHERE from_address = ? OR to_address = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (address.lower(), address.lower())).fetchall()
    db.close()
    
    return jsonify({
        'transactions': [dict(tx) for tx in transactions]
    })

@app.route('/api/transaction/<tx_hash>', methods=['GET'])
def get_transaction(tx_hash):
    """Get specific transaction details"""
    db = get_db()
    transaction = db.execute('SELECT * FROM transactions WHERE tx_hash = ?',
                            (tx_hash,)).fetchone()
    db.close()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    return jsonify(dict(transaction))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    init_db()
    print("ETH Mock Wallet Backend Starting...")
    print("Database initialized")
    print("Server running on http://localhost:5000")
    app.run(debug=True, port=5000)