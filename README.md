# ETHWallet
A simple mock ETH web3 wallet application. 
ETH Mock Wallet is a full-stack web application that mimics the functionality of a real Ethereum wallet without interacting with the actual blockchain.

Key Features

✅ Wallet Creation: Create multiple Ethereum wallets with unique addresses
✅ Balance Management: Track ETH balances with real-time USD conversion
✅ Send Transactions: Transfer ETH between wallets with signature verification
✅ Price Integration: Live ETH-to-USD price fetching from CoinGecko API
✅ Transaction History: View complete send/receive history
✅ Email Notifications: Optional email alerts for transactions

🏗️ Architecture
Backend (Python/Flask)

1. RESTful API for wallet operations
2. SQLite database for data persistence
3. Web3.py for signature verification
4. Real-time cryptocurrency price fetching

Frontend (HTML/CSS/JavaScript)

1. Clean, responsive user interface
2. Ethers.js for blockchain interactions
3. Real-time balance updates
4. Transaction management

Example Workflow

-> Create wallet A with address 0x742d35...
-> Create wallet B with address 0x5aAeb6...
-> Check balance of wallet A (should be 100 ETH)
-> Send 10 ETH from A to B
-> Check balances (A: 90 ETH, B: 110 ETH)
-> View transaction history



