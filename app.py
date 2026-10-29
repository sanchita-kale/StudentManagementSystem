import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.config["DATABASE"] = os.environ.get(
    "STUDENT_DB_PATH", str(Path(app.instance_path) / "student_management.db")
)


def db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def q(sql, args=(), fetch=False):
    connection = db()
    try:
        cursor = connection.execute(sql, args)
        data = [dict(row) for row in cursor.fetchall()] if fetch else None
        connection.commit()
        return data
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = db()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                course TEXT,
                semester TEXT,
                address TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                student_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                teacher TEXT,
                semester TEXT
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                exam_type TEXT,
                marks REAL,
                total_marks REAL,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                day TEXT,
                start_time TEXT,
                end_time TEXT,
                room TEXT,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                title TEXT,
                description TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                exam_name TEXT,
                exam_date TEXT,
                start_time TEXT,
                room TEXT,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                notice_date TEXT,
                audience TEXT NOT NULL DEFAULT 'All'
            );
            CREATE TABLE IF NOT EXISTS fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                fee_type TEXT,
                amount REAL,
                paid_amount REAL NOT NULL DEFAULT 0,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO students(name, email, phone, course, semester, address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Aarav Patil", "aarav@example.com", "9876543210", "BCA", "Semester 5", "Pune"),
                ("Sanchita Kale", "sanchita@example.com", "9876543211", "BCA", "Semester 5", "Shirdi"),
            ],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO subjects(name, code, teacher, semester)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("Python Programming", "BCA501", "Prof. Sharma", "Semester 5"),
                ("Database Management", "BCA502", "Prof. Patil", "Semester 5"),
                ("Web Technology", "BCA503", "Prof. Deshmukh", "Semester 5"),
            ],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO users(username, password, role, student_id)
            VALUES (?, ?, 'admin', NULL)
            """,
            ("admin", generate_password_hash("admin123")),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO users(username, password, role, student_id)
            VALUES (?, ?, 'user', (SELECT id FROM students WHERE email = 'aarav@example.com'))
            """,
            ("student", generate_password_hash("user123")),
        )
        if connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO notices(title, content, notice_date, audience)
                VALUES (?, ?, ?, ?)
                """,
                [
                    ("Welcome Notice", "Welcome to the Student Management System.", "2026-09-01", "All"),
                    ("Internal Exam", "Internal examinations will be conducted as per timetable.", "2026-09-05", "Students"),
                ],
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapped


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return wrapped


@app.context_processor
def ctx():
    return {"current_user": session.get("username"), "role": session.get("role")}


@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = q("SELECT * FROM users WHERE username = ?", (request.form["username"],), True)
        if users and check_password_hash(users[0]["password"], request.form["password"]):
            user = users[0]
            session.update(
                user_id=user["id"],
                username=user["username"],
                role=user["role"],
                student_id=user["student_id"],
            )
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    names = ["students", "attendance", "marks", "subjects", "timetable", "assignments", "exams", "notices", "fees"]
    stats = {name: q(f"SELECT COUNT(*) AS c FROM {name}", fetch=True)[0]["c"] for name in names}
    return render_template("dashboard.html", stats=stats)


@app.route("/students")
@login_required
def students():
    rows = q("SELECT * FROM students ORDER BY id DESC", fetch=True)
    return render_template("students.html", rows=rows)


@app.route("/students/add", methods=["POST"])
@login_required
@admin_required
def student_add():
    form = request.form
    q(
        """
        INSERT INTO students(name, email, phone, course, semester, address)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (form["name"], form["email"], form.get("phone"), form.get("course"), form.get("semester"), form.get("address")),
    )
    return redirect(url_for("students"))


@app.route("/students/edit/<int:id>", methods=["POST"])
@login_required
@admin_required
def student_edit(id):
    form = request.form
    q(
        """
        UPDATE students SET name = ?, email = ?, phone = ?, course = ?, semester = ?, address = ?
        WHERE id = ?
        """,
        (
            form["name"],
            form["email"],
            form.get("phone"),
            form.get("course"),
            form.get("semester"),
            form.get("address"),
            id,
        ),
    )
    return redirect(url_for("students"))


@app.route("/students/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def student_delete(id):
    q("DELETE FROM students WHERE id = ?", (id,))
    return redirect(url_for("students"))


M = {
    "attendance": (
        "Attendance",
        "attendance",
        ["student_id", "subject_id", "date", "status"],
        """SELECT a.*, s.name AS student_name, sub.name AS subject_name
           FROM attendance a JOIN students s ON s.id = a.student_id
           JOIN subjects sub ON sub.id = a.subject_id ORDER BY a.date DESC""",
        "INSERT INTO attendance(student_id, subject_id, date, status) VALUES (?, ?, ?, ?)",
        "UPDATE attendance SET student_id = ?, subject_id = ?, date = ?, status = ? WHERE id = ?",
    ),
    "marks": (
        "Marks",
        "marks",
        ["student_id", "subject_id", "exam_type", "marks", "total_marks"],
        """SELECT m.*, s.name AS student_name, sub.name AS subject_name
           FROM marks m JOIN students s ON s.id = m.student_id
           JOIN subjects sub ON sub.id = m.subject_id ORDER BY m.id DESC""",
        "INSERT INTO marks(student_id, subject_id, exam_type, marks, total_marks) VALUES (?, ?, ?, ?, ?)",
        "UPDATE marks SET student_id = ?, subject_id = ?, exam_type = ?, marks = ?, total_marks = ? WHERE id = ?",
    ),
    "subjects": (
        "Subjects",
        "subjects",
        ["name", "code", "teacher", "semester"],
        "SELECT * FROM subjects ORDER BY id DESC",
        "INSERT INTO subjects(name, code, teacher, semester) VALUES (?, ?, ?, ?)",
        "UPDATE subjects SET name = ?, code = ?, teacher = ?, semester = ? WHERE id = ?",
    ),
    "timetable": (
        "Timetable",
        "timetable",
        ["subject_id", "day", "start_time", "end_time", "room"],
        """SELECT t.*, sub.name AS subject_name FROM timetable t
           JOIN subjects sub ON sub.id = t.subject_id ORDER BY t.id DESC""",
        "INSERT INTO timetable(subject_id, day, start_time, end_time, room) VALUES (?, ?, ?, ?, ?)",
        "UPDATE timetable SET subject_id = ?, day = ?, start_time = ?, end_time = ?, room = ? WHERE id = ?",
    ),
    "assignments": (
        "Assignments",
        "assignments",
        ["subject_id", "title", "description", "due_date", "status"],
        """SELECT a.*, sub.name AS subject_name FROM assignments a
           JOIN subjects sub ON sub.id = a.subject_id ORDER BY a.id DESC""",
        "INSERT INTO assignments(subject_id, title, description, due_date, status) VALUES (?, ?, ?, ?, ?)",
        "UPDATE assignments SET subject_id = ?, title = ?, description = ?, due_date = ?, status = ? WHERE id = ?",
    ),
    "exams": (
        "Exams",
        "exams",
        ["subject_id", "exam_name", "exam_date", "start_time", "room"],
        """SELECT e.*, sub.name AS subject_name FROM exams e
           JOIN subjects sub ON sub.id = e.subject_id ORDER BY e.exam_date""",
        "INSERT INTO exams(subject_id, exam_name, exam_date, start_time, room) VALUES (?, ?, ?, ?, ?)",
        "UPDATE exams SET subject_id = ?, exam_name = ?, exam_date = ?, start_time = ?, room = ? WHERE id = ?",
    ),
    "notices": (
        "Notices",
        "notices",
        ["title", "content", "notice_date", "audience"],
        "SELECT * FROM notices ORDER BY notice_date DESC",
        "INSERT INTO notices(title, content, notice_date, audience) VALUES (?, ?, ?, ?)",
        "UPDATE notices SET title = ?, content = ?, notice_date = ?, audience = ? WHERE id = ?",
    ),
    "fees": (
        "Fees",
        "fees",
        ["student_id", "fee_type", "amount", "paid_amount", "due_date", "status"],
        """SELECT f.*, s.name AS student_name FROM fees f
           JOIN students s ON s.id = f.student_id ORDER BY f.due_date""",
        "INSERT INTO fees(student_id, fee_type, amount, paid_amount, due_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        "UPDATE fees SET student_id = ?, fee_type = ?, amount = ?, paid_amount = ?, due_date = ?, status = ? WHERE id = ?",
    ),
}

STATUS_OPTIONS = {
    "attendance": ["Present", "Absent", "Late"],
    "assignments": ["Pending", "Submitted", "Completed"],
    "fees": ["Pending", "Partial", "Paid"],
}


@app.route("/<mod>")
@login_required
def module(mod):
    if mod not in M:
        return "Not found", 404
    title, table, cols, select_sql, insert_sql, update_sql = M[mod]
    return render_template(
        "module.html",
        mod=mod,
        title=title,
        cols=cols,
        rows=q(select_sql, fetch=True),
        students=q("SELECT id, name FROM students ORDER BY name", fetch=True),
        subjects=q("SELECT id, name, code FROM subjects ORDER BY name", fetch=True),
        status_options=STATUS_OPTIONS.get(mod, []),
    )


@app.route("/<mod>/add", methods=["POST"])
@login_required
@admin_required
def add(mod):
    if mod not in M:
        return "Not found", 404
    _, _, cols, _, insert_sql, _ = M[mod]
    q(insert_sql, tuple(request.form.get(column) for column in cols))
    return redirect(url_for("module", mod=mod))


@app.route("/<mod>/edit/<int:id>", methods=["POST"])
@login_required
@admin_required
def edit(mod, id):
    if mod not in M:
        return "Not found", 404
    _, _, cols, _, _, update_sql = M[mod]
    q(update_sql, tuple(request.form.get(column) for column in cols) + (id,))
    return redirect(url_for("module", mod=mod))


@app.route("/<mod>/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete(mod, id):
    if mod not in M:
        return "Not found", 404
    q(f"DELETE FROM {M[mod][1]} WHERE id = ?", (id,))
    return redirect(url_for("module", mod=mod))


@app.route("/profile")
@login_required
def profile():
    student_id = session.get("student_id")
    student = q("SELECT * FROM students WHERE id = ?", (student_id,), True) if student_id else []
    return render_template("profile.html", student=student[0] if student else None)


if __name__ == "__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
