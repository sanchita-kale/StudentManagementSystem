# CampusDesk — Student Management System

A student and academic-record management web app built with Flask, SQLite, and responsive HTML/CSS templates. SQLite is included with Python, so you do **not** need MySQL, MySQL Workbench, XAMPP, or phpMyAdmin to run the application.

## Features

- Admin and student demo sign-in
- Dashboard with counts for students and academic records
- Student directory and profile
- Create, view, edit, and delete records for students, attendance, marks, subjects, timetable, assignments, exams, notices, and fees (admin)
- Local SQLite database initialized with example students, subjects, notices, and demo accounts on first launch
- Responsive pages with local campus and classroom photography

## Run on Windows

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks environment activation, run the venv's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open <http://127.0.0.1:5000>.

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Student | `student` | `user123` |

These are development/demo accounts. Do not use them for a public deployment.

## Database

The app creates `instance/student_management.db` and its tables automatically when you start it. Data stays in that file between runs. Set `STUDENT_DB_PATH` before starting the app if you want the database saved elsewhere:

```powershell
$env:STUDENT_DB_PATH = "C:\path\to\student_management.db"
python app.py
```

The original MySQL schema is retained in `database/student_management.sql` as a reference, but the application currently runs on SQLite.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The tests use a temporary SQLite database and do not need any external database service.

## Production note

Set a strong random `SECRET_KEY`, disable debug mode (it is disabled by default), and replace the demo accounts before deploying the application publicly.
