# Job Tracker Web App (Flask + Azure MySQL + Render)

A simple web application built with Flask to track job applications.
It supports full CRUD operations and sends automated email reminders for follow-ups.

---

## Features

* Add, edit, delete job applications
* Search and filter applications by status
* Secure login system (session-based)
* Day by day email reminders (Day 3, 5, 7 follow-ups)
* Manual trigger for reminder emails
* Azure MySQL database integration

Core functionality is implemented in:

* `app.py` (routes + auth) 
* `db.py` (database connection) 
* `reminders.py` (email scheduler) 

---

## Tech Stack

* Python 3
* Flask
* MySQL (Azure MySQL Flexible Server)
* Gunicorn (production server)
* APScheduler (background jobs)
* Render (deployment)

Dependencies are defined in `requirements.txt` 

---

## 📁 Project Structure

```
.
├── app.py              # Main Flask app (routes, login, CRUD)
├── db.py               # Database helper
├── reminders.py        # Email reminders + scheduler
├── wsgi.py             # Entry point for Gunicorn
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
├── templates/
└── static/
```

---

## Environment Variables

Create a `.env` file based on `.env.example` and fill in:

### App Config

```
FLASK_SECRET_KEY=your_secret_key
APP_PASSWORD=your_login_password
```

### Database (Azure MySQL)

```
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database
DB_SSL_CA=path_to_cert.pem
```

### 📧 Email (SMTP)

```
EMAIL_FROM=your_email
EMAIL_TO=your_email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_app_password
```

### Reminder Scheduler

```
REMINDER_HOUR=9
REMINDER_MINUTE=0
```

---

## Run Locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

App runs at:

```
http://localhost:5000
```

---


---

### 2. Create Render Web Service

* Connect GitHub repo
* Environment: **Python**

**Build Command**

```
pip install -r requirements.txt
```

**Start Command**

```
gunicorn wsgi:app
```

(`wsgi.py` is used as entry point) 

---

### 3. Add Environment Variables in Render

Replicate all values from your `.env` into the Render dashboard.

---

### 4. Azure Firewall

Approve outer access:

* Go to Azure Portal → MySQL Server → Networking
* Add rule:

```
0.0.0.0 → 255.255.255.255
```

---

## Reminder System

The app sends daily email reminders for follow-ups.

Logic (from code):

* Finds applications where:

  * `date_applied` = 3, 5, or 7 days ago
  * status is still open (`Applied`, `Pending Response`, etc.) 

* Sends a single digest email

You can also trigger manually:

```
POST /send-reminders
```

---

## 🔐 Authentication

* Simple password-based login
* Controlled via `APP_PASSWORD`
* Uses Flask sessions with 30-day duration 

---

## ⚠️ Common Issues

| Issue                 | Cause            | Fix                        |
| --------------------- | ---------------- | -------------------------- |
| DB connection fails   | Firewall         | Allow IP in Azure          |
| SSL error             | Missing cert     | Add `DigiCertGlobalRootCA` |
| Emails not sending    | Wrong SMTP       | Use Gmail App Password     |
| App crashes on Render | Missing gunicorn | Already included           |

---

## 📌 Notes

* Debug mode is enabled locally only
* Scheduler starts automatically on app startup 


## 📄 License

This project is for personal use and learning and licensed under MIT.
