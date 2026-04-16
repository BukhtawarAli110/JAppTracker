# Job Tracker — Flask + Azure MySQL

A minimal web app for managing the `JobsData` table in your `job-tracker`
Azure MySQL database. Supports Create, Read, Update, Delete, and sends
daily email reminders for Day 3 / 5 / 7 follow-ups on applications still
pending a response.

---

## 1. Prerequisites

- **Python 3.10+** installed
- **Azure MySQL firewall:** add your current client IP
  (Azure Portal → your MySQL server → *Networking*)
- **Azure SSL certificate** (required by Azure MySQL).
  Download `DigiCertGlobalRootCA.crt.pem` and place it in the project folder:
  <https://www.digicert.com/kb/digicert-root-certificates.htm>

---

## 2. Setup

```bash
cd "D:/Claude Work - Projects/Job-Tracker-App"

# Create a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
copy .env.example .env           # Windows
# cp .env.example .env           # Linux / macOS
```

Open `.env` and fill in:

- `DB_PASSWORD` — your Azure MySQL password
- SMTP section — Gmail app password works best
  (create one at <https://myaccount.google.com/apppasswords>)

---

## 3. Run

```bash
python app.py
```

Open <http://localhost:5000> in your browser.

To access from your phone on the same Wi-Fi network:
`http://<your-pc-ip>:5000` (find IP with `ipconfig`).

---

## 4. Features

| Feature | How to use |
|---|---|
| **View / search** | Home page. Filter by text and status. |
| **Add** | Click "+ New Application" |
| **Edit** | Click "Edit" on any row |
| **Delete** | Click "Delete" (asks for confirmation) |
| **Email reminders** | Sent automatically every day at 09:00 (change `REMINDER_HOUR` in `.env`) |
| **Test email now** | Click "Send Reminder Email Now" button in the header |

Reminder logic: includes applications where
`date_applied` was exactly 3, 5, or 7 days ago AND
`post_status` is still one of `Applied`, `Application Viewed`, or
`Pending Response`.

---

## 5. Project Structure

```
Job-Tracker-App/
├── app.py                 # Flask routes (CRUD)
├── db.py                  # MySQL connection helper
├── reminders.py           # Email scheduler + digest builder
├── requirements.txt
├── .env.example           # Copy to .env and fill in
├── DigiCertGlobalRootCA.crt.pem   # You download this
├── templates/
│   ├── base.html
│   ├── index.html         # Applications table
│   └── form.html          # New / Edit form
└── static/
    └── style.css
```

---

## 6. Later — Deploying to your Debian server

When you're ready, the process is roughly:

1. Copy the folder to the server
2. Install Python + create the venv there
3. Run under `gunicorn` behind `nginx` as a systemd service
4. Add the server's public IP to the Azure MySQL firewall
5. (Optional) Add auth since it will be reachable from the internet

Happy to write the deployment files when you reach that step.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `Access denied for user` | Wrong username/password in `.env` |
| `Can't connect to MySQL server` | Your IP isn't whitelisted in Azure Networking |
| `SSL connection error` | `DigiCertGlobalRootCA.crt.pem` missing or path wrong |
| Email doesn't send | Use a **Gmail App Password**, not your Gmail password |
| Table columns don't match | Run `Job-Tracker.sql` first so `JobsData` exists |
