# Finance_Tracker_Zorvyn: Technical Documentation

**Version 1.0.0**  
*Architecture | Data Flows | API Reference | Role-Based Access | Public-First Mode*

---

## 1. Introduction
This document provides a complete technical reference for **Finance_Tracker_Zorvyn** — a public-first financial management dashboard built with FastAPI, SQLAlchemy, and SQLite. It covers architectural decisions, data models, and the "Public-First" security model.

The system is organized around one core principle: **Separation of Concerns**. 
- **Routers**: Handle HTTP requests/responses only.
- **Services**: Contain all business logic.
- **Models**: Define the database schema.
- **Schemas**: Define input/output data contracts (Pydantic).

All of these components reside within the `app/` package to ensure a clean project root.

---

## 2. Tech Stack

| Layer | Technology | Reason |
| :--- | :--- | :--- |
| **Framework** | FastAPI | Async-ready, auto-generated Swagger docs, and native Pydantic integration. |
| **ORM** | SQLAlchemy 2.0 | Mature ORM with clean declarative models. Swappable to PostgreSQL. |
| **Database** | SQLite | Zero-config, file-based database ideal for demonstration and local use. |
| **Frontend** | Vanilla JS / HTML / CSS | High performance, zero build-step overhead, and custom Glassmorphism UI. |
| **Security** | JWT (python-jose) | Stateless authentication for Administrative overrides. |

---

## 3. Project Structure
The project is organized into a clean, package-based architecture.

```text
finance_tracker/
├── app/               # Core application logic package
│   ├── main.py        # App entry point & global error handlers
│   ├── exceptions.py  # Custom exception classes
│   ├── core/          # Global configuration, database setup, and seed.py
│   ├── models/        # SQLAlchemy database models
│   ├── schemas/       # Pydantic request/response models
│   ├── routers/       # API route handlers (Auth, Transactions, Analytics)
│   ├── services/      # Pure business logic (Processing, Database IO)
│   └── dependencies/  # Auth & DB dependency injection
├── docs/              # Detailed Technical Documentation
├── tests/             # Automated verification tests (e2e_test.py)
├── frontend/          # Static web assets (HTML, CSS, JS)
├── requirements.txt   # Project dependencies
├── finance_tracker.db # SQLite database (auto-generated)
└── README.md          # Quick start guide
```

---

## 4. Public-First Security Model
Unlike traditional "Auth-First" systems, **Finance_Tracker_Zorvyn** prioritizes immediate usability for guest users.

### 4.1 Role Matrix

| Action | Public (Guest) | Admin |
| :--- | :---: | :---: |
| View Dashboard Summary | ✅ | ✅ |
| View Recent Activity | ✅ | ✅ |
| Add New Transaction | ✅ | ✅ |
| Export Data (CSV/JSON) | ✅ | ✅ |
| **Edit Existing Record** | ❌ | ✅ |
| **Delete Record** | ❌ | ✅ |

### 4.2 Authentication Logic
- **Public Access**: Handled by a "Public User" fallback in `app/dependencies/auth.py`. If no JWT is provided, the system defaults to the seeded `user@demo.com` context for Read/Create operations. This allows instant usability for non-admin reviewers.
- **Admin Access**: Requires a valid JWT token. Endpoints for `PUT` and `DELETE` are strictly gated with a `require_role("admin")` dependency.

---

## 5. Data Lifecycle & Volatility

> [!IMPORTANT]
> **Demo Mode Volatility**: In its current "Professional Demo" configuration, the application **drops all tables and re-seeds the database on every restart**. This ensures every reviewer starts with a clean slate but means that manually entered data is lost when the server stops.

### 5.1 Data Models
- **User**: Stores profile information and Hashed Passwords (bcrypt).
- **Transaction**: Stores financial records (Income/Expense), categories, and notes. Every transaction is linked to a user.

---

## 6. API Reference (Core Endpoints)

### 📈 Analytics
- `GET /analytics/summary`: High-level totals (Income, Expense, Balance).
- `GET /analytics/category`: Distribution by category (Income/Expense breakdown).
- `GET /analytics/monthly`: Last 6 months of trends for Chart.js.
- `GET /analytics/trend`: Spending trend (this month vs last month delta).
- `GET /analytics/recent`: Chronological activity with running balances.

### 💸 Transactions
- `GET /transactions`: Paginated list of all records with filters/search.
- `GET /transactions/export`: Export records as CSV or JSON format.
- `POST /transactions`: Public endpoint to add a new record.
- `PUT /transactions/{id}`: **(Admin Only)** Modify a record.
- `DELETE /transactions/{id}`: **(Admin Only)** Permanent removal.

---

## 7. Development & Verification

### End-to-End Testing
The system includes an `e2e_test.py` script that automatically verifies:
1. Public access (No token required for Read/Create).
2. Security gating (401/403 for unauthorized Edit/Delete).
3. Admin login and successful maintenance operations.

```bash
# How to verify the system
python e2e_test.py
```

### Health Check
A dedicated health endpoint is available at `/api/health` to verify server uptime and database connectivity.
