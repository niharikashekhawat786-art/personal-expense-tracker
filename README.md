# Personal Expense Tracker Web App

A secure, Flask-based web application for managing personal expenses. Users can register, log in, track expenses, visualize spending, filter records, and export their expenses to CSV.

## Features

- **User authentication:** Registration, login, logout, and password hashing.
- **Expense management:** Add, view, edit, and delete expenses.
- **Data privacy:** Users can access and manage only their own expenses.
- **Search and filters:** Filter expenses by category and date, and search expense descriptions.
- **Dashboard:** View spending summaries and charts using Chart.js.
- **CSV export:** Download expense records for personal reporting.
- **Responsive interface:** Bootstrap-based user interface.
- **Input validation:** Validate expense details and handle invalid submissions.
- **Security:** Environment-based secret key, CSRF protection, and secure session-cookie settings.

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- SQLite
- HTML and CSS
- Bootstrap
- Chart.js

## Requirements

- Python 3.10 or newer
- Internet connection for Bootstrap and Chart.js CDN assets

## Installation and Setup

### 1. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Generate a strong secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `.env`:

```text
SECRET_KEY=your-generated-secret-key
```

Replace the example value with your generated key. Never commit `.env` or expose your secret key publicly.

### 4. Run the application

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Press `Ctrl+C` in the terminal to stop the server.

## How to Use

1. Create an account with your name, email, and password.
2. Log in to the application.
3. Add expenses with a description, amount, category, date, and optional notes.
4. Review spending summaries and charts on the dashboard.
5. Search, filter, edit, or delete your expense records.
6. Export expenses to CSV when needed.
7. Log out when finished.

## Database

The application creates the SQLite database at `instance/expenses.db` when initialized.

Keep this file to preserve your local records. Deleting it can permanently remove your local expense data. The `instance/` directory is excluded from Git.

## Running Tests

Run the automated tests with:

```powershell
python -m pytest -v
```

Alternatively, if your tests support standard `unittest` discovery:

```powershell
python -m unittest discover -s tests -v
```

## Security Notes

- This is a learning and portfolio project, not a certified financial application.
- CSRF protection is enabled for form submissions.
- The secret key is loaded from environment configuration.
- Session cookies use `HttpOnly` and `SameSite=Lax` settings.
- For production, deploy behind HTTPS, enable secure cookies, configure production-grade logging, and use a suitable production database such as PostgreSQL.
- Never enable Flask debug mode in production.
- Do not commit `.env`, local databases, or virtual-environment files.

## Future Improvements

- PostgreSQL deployment
- Automated backups
- Budget limits and monthly spending reports
- Additional test coverage
- Production deployment and monitoring
