# Karandeni Investment – Financial & Micro-Credit Management System

A full-stack enterprise web application designed for **Karandeni Investment**, providing comprehensive financial management, field collection, customer KYC onboarding, micro-credit loan contracts, automated repayment calculations, teller savings management, and real-time SMS notifications.

---

## 🌟 System Architecture & Technology Stack

- **Frontend**: Responsive Single-Page Application (SPA) built with Semantic HTML5, Vanilla CSS3 (Custom Glassmorphic & Modern Theme), and Pure JavaScript.
- **Backend**: Python 3 with Flask modular REST API Architecture (Blueprints).
- **Database**: MongoDB (Scalable document store with automated indexing).
- **Authentication**: Stateless JSON Web Tokens (JWT, HS256) + bcrypt password hashing.
- **SMS Gateway**: SMSlenz Sri Lanka integration for instant automated transaction SMS alerts.

---

## 🚀 Quick Start Guide

### 1. Prerequisites (macOS)
Ensure MongoDB and Python 3 are installed:
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

### 2. Environment Configuration
Inspect or adjust environment variables in `backend/.env`:
```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=karandeni_investment
JWT_SECRET=your_super_secret_jwt_key
FLASK_PORT=5001

# SMS Gateway Configuration
SMSLENZ_USER_ID=2173
SMSLENZ_API_KEY=39192d1c-a7c2-40c9-9f7d-3d00eee5ad16
SMSLENZ_SENDER_ID=KarandeniInv
SMSLENZ_API_URL=https://smslenz.lk/api/send-sms
```

### 3. Initialize & Seed Clean Database
Initialize the fresh database with default Administrator credentials and default branch (`KARANDENIYA`):
```bash
cd backend
python3 seed.py
```
*(To wipe all transactional data and reset to a clean state anytime, run: `python3 seed.py --reset`)*

### 4. Start the Backend API Server
```bash
cd backend
python3 app.py
```
*API runs at `http://localhost:5001` (or your configured `FLASK_PORT`).*

### 5. Launch the Frontend
Open `loginpage.html` in your browser, or start via a local HTTP server:
```bash
# Using python http server:
python3 -m http.server 8000
```
Then navigate to: `http://localhost:8000/loginpage.html`

---

## ⚡ One-Command Automatic Startup

You can start both MongoDB and the Backend Server with one command:
```bash
./start.sh
```

---

## 🔐 Default Administrator Login

| Field | Value |
|-------|-------|
| **URL** | `loginpage.html` |
| **Username** | `asindu` |
| **Password** | `1234` |
| **Role** | System Administrator |
| **Default Branch** | `KARANDENIYA` (`KDN`) |

---

## 📂 Core Business Modules

1. **Customer KYC & Onboarding**:
   - Register clients with full NIC validation, contact details, spouse/guarantor, and bank account information.
   - Assign clients to Community Based Organizations (CBOs) and sub-groups (`G-1`, `G-2`).

2. **CBO (Center) Management**:
   - Setup centers/meeting schedules (days, times, center leaders).
   - Assign dedicated Credit Officers per center.
   - Track center attendance and group formations.

3. **Micro-Credit & Loan Engine**:
   - Issue micro loans with dynamic interest calculations, document charges, and tenor matrix (e.g. 13-week or 24-week terms).
   - Automated Repayment Matrix preview and printable Loan Agreements.
   - Real-time loan lifecycle tracking (`Active`, `Disbursed`, `Settled`).

4. **Cashier Desk & Group Collections**:
   - Dedicated Loan Disbursement verification workflow.
   - Field collection sheets & group payments processing.
   - Instant calculation of expected due, arrears, paid amounts, and outstanding balance.

5. **Automated SMS Notification Service**:
   - Instant SMS receipt dispatched to customer's mobile upon payment recording with remaining balance.

6. **Savings & Teller Operations**:
   - Create customer savings accounts.
   - Record teller deposits and withdrawals with real-time balance validation.

7. **Financial & Operational Reports**:
   - Daily Investment Report & Capital Growth.
   - Credit Officer Collection Journal.
   - Cash Movement Ledger.
   - Arrears / Not Paid Defaulter analysis.
