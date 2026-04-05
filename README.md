# Finance_Tracker_Zorvyn

Modern, role-based, public-first finance tracking dashboard.

---

### 🚀 Quick Start (Run from Scratch)

#### 1. Navigate to the project directory
```bash
cd finance_tracker
```

#### 2. Create and Activate Virtual Environment
- **Windows**: `python -m venv venv` and `.\venv\Scripts\activate`
- **macOS/Linux**: `python3 -m venv venv` and `source venv/bin/activate`

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Run the Application
```bash
uvicorn app.main:app --port 8000
```
*The server will start at [http://localhost:8000](http://localhost:8000)*

---

### 🔑 Admin Credentials
The dashboard is **Public-First** (anyone can view and add records). Admin login is required only for editing or deleting records.
- **Email**: `admin@demo.com`
- **Password**: `Admin1234`

---

### 📖 Full Documentation
For a deep dive into the **Architecture**, **Security Model**, and **API Reference**, please see:
👉 **[TECHNICAL_DOCUMENTATION.md](./docs/TECHNICAL_DOCUMENTATION.md)**

---

### 🧪 Verification
Run the automated test suite to verify the system (ensure server is running first):
```bash
python tests/e2e_test.py
```
