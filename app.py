from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date
from pathlib import Path

# --------------------------------
# 1. Flask application configuration
# --------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = "student-study-planner-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# --------------------------------
# 2. Database connection
# --------------------------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# --------------------------------
# 3. Create database tables
# --------------------------------

def init_db():
    connection = get_db()

    connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#4f46e5'
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER,
            study_date TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER,
            title TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            target_date TEXT,
            completed INTEGER DEFAULT 0
        );
    """)

    connection.commit()
    connection.close()


# --------------------------------
# 4. User class for Flask-Login
# --------------------------------

class User(UserMixin):

    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):

    connection = get_db()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    if user:
        return User(user["id"], user["name"], user["email"])

    return None


# --------------------------------
# 5. Home page
# --------------------------------

@app.route("/")
def home():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# --------------------------------
# 6. Student registration
# --------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        connection = get_db()

        try:
            connection.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name, email, password_hash)
            )

            connection.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This email is already registered.", "danger")

        finally:
            connection.close()

    return render_template("register.html")


# --------------------------------
# 7. Student login
# --------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password_hash"], password):

            student = User(
                user["id"],
                user["name"],
                user["email"]
            )

            login_user(student)

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# --------------------------------
# 8. Student logout
# --------------------------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have logged out successfully.", "success")

    return redirect(url_for("login"))


# --------------------------------
# 9. Dashboard
# --------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db()

    total_subjects = connection.execute(
        "SELECT COUNT(*) FROM subjects WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    total_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    completed_tasks = connection.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND status = 'Completed'
        """,
        (current_user.id,)
    ).fetchone()[0]

    pending_tasks = total_tasks - completed_tasks

    upcoming_exams = connection.execute(
        """
        SELECT exams.*, subjects.name AS subject_name
        FROM exams
        LEFT JOIN subjects ON exams.subject_id = subjects.id
        WHERE exams.user_id = ? AND exams.exam_date >= ?
        ORDER BY exams.exam_date
        LIMIT 5
        """,
        (current_user.id, date.today().isoformat())
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total_subjects=total_subjects,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        upcoming_exams=upcoming_exams
    )


# --------------------------------
# 10. Manage subjects
# --------------------------------

@app.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects():

    connection = get_db()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        color = request.form.get("color", "#4f46e5")

        if name:
            connection.execute(
                """
                INSERT INTO subjects (user_id, name, color)
                VALUES (?, ?, ?)
                """,
                (current_user.id, name, color)
            )

            connection.commit()
            flash("Subject added successfully.", "success")

        connection.close()
        return redirect(url_for("subjects"))

    subject_list = connection.execute(
        "SELECT * FROM subjects WHERE user_id = ? ORDER BY name",
        (current_user.id,)
    ).fetchall()

    connection.close()

    return render_template("subjects.html", subjects=subject_list)


@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM subjects WHERE id = ? AND user_id = ?",
        (subject_id, current_user.id)
    )

    connection.commit()
    connection.close()

    flash("Subject deleted.", "success")

    return redirect(url_for("subjects"))


# --------------------------------
# 11. Manage tasks
# --------------------------------

@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():

    connection = get_db()

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "Medium")
        subject_id = request.form.get("subject_id") or None

        if title:

            connection.execute(
                """
                INSERT INTO tasks
                (user_id, subject_id, title, description, due_date, priority)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    subject_id,
                    title,
                    description,
                    due_date,
                    priority
                )
            )

            connection.commit()
            flash("Task added successfully.", "success")

        connection.close()
        return redirect(url_for("tasks"))

    task_list = connection.execute(
        """
        SELECT tasks.*, subjects.name AS subject_name
        FROM tasks
        LEFT JOIN subjects ON tasks.subject_id = subjects.id
        WHERE tasks.user_id = ?
        ORDER BY
            CASE WHEN tasks.status = 'Pending' THEN 0 ELSE 1 END,
            tasks.due_date
        """,
        (current_user.id,)
    ).fetchall()

    subject_list = connection.execute(
        "SELECT * FROM subjects WHERE user_id = ?",
        (current_user.id,)
    ).fetchall()

    connection.close()

    return render_template(
        "tasks.html",
        tasks=task_list,
        subjects=subject_list
    )


@app.route("/tasks/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id):

    connection = get_db()

    task = connection.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, current_user.id)
    ).fetchone()

    if task:

        new_status = (
            "Completed"
            if task["status"] == "Pending"
            else "Pending"
        )

        connection.execute(
            "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
            (new_status, task_id, current_user.id)
        )

        connection.commit()

    connection.close()

    return redirect(url_for("tasks"))


@app.route("/tasks/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, current_user.id)
    )

    connection.commit()
    connection.close()

    flash("Task deleted.", "success")

    return redirect(url_for("tasks"))


# --------------------------------
# 12. Study planner
# --------------------------------

@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():

    connection = get_db()

    if request.method == "POST":

        subject_id = request.form.get("subject_id") or None
        study_date = request.form.get("study_date")
        duration = request.form.get("duration")
        notes = request.form.get("notes", "")

        try:
            duration = int(duration)

            if not study_date or duration <= 0:
                raise ValueError

            connection.execute(
                """
                INSERT INTO study_sessions
                (user_id, subject_id, study_date, duration_minutes, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    subject_id,
                    study_date,
                    duration,
                    notes
                )
            )

            connection.commit()
            flash("Study session recorded.", "success")

        except (ValueError, TypeError):
            flash("Enter a valid date and study duration.", "danger")

        connection.close()
        return redirect(url_for("planner"))

    sessions = connection.execute(
        """
        SELECT study_sessions.*, subjects.name AS subject_name
        FROM study_sessions
        LEFT JOIN subjects ON study_sessions.subject_id = subjects.id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.study_date DESC
        """,
        (current_user.id,)
    ).fetchall()

    subject_list = connection.execute(
        "SELECT * FROM subjects WHERE user_id = ?",
        (current_user.id,)
    ).fetchall()

    connection.close()

    return render_template(
        "planner.html",
        sessions=sessions,
        subjects=subject_list
    )


# --------------------------------
# 13. Manage examinations
# --------------------------------

@app.route("/exams", methods=["GET", "POST"])
@login_required
def exams():

    connection = get_db()

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        exam_date = request.form.get("exam_date")
        subject_id = request.form.get("subject_id") or None
        notes = request.form.get("notes", "")

        if title and exam_date:

            connection.execute(
                """
                INSERT INTO exams
                (user_id, subject_id, title, exam_date, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (current_user.id, subject_id, title, exam_date, notes)
            )

            connection.commit()
            flash("Exam added successfully.", "success")

        connection.close()
        return redirect(url_for("exams"))

    exam_list = connection.execute(
        """
        SELECT exams.*, subjects.name AS subject_name
        FROM exams
        LEFT JOIN subjects ON exams.subject_id = subjects.id
        WHERE exams.user_id = ?
        ORDER BY exams.exam_date
        """,
        (current_user.id,)
    ).fetchall()

    subject_list = connection.execute(
        "SELECT * FROM subjects WHERE user_id = ?",
        (current_user.id,)
    ).fetchall()

    connection.close()

    return render_template(
        "exams.html",
        exams=exam_list,
        subjects=subject_list
    )


@app.route("/exams/delete/<int:exam_id>", methods=["POST"])
@login_required
def delete_exam(exam_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM exams WHERE id = ? AND user_id = ?",
        (exam_id, current_user.id)
    )

    connection.commit()
    connection.close()

    flash("Exam deleted.", "success")

    return redirect(url_for("exams"))


# --------------------------------
# 14. Manage study goals
# --------------------------------

@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():

    connection = get_db()

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        target_date = request.form.get("target_date", "")

        if title:

            connection.execute(
                """
                INSERT INTO goals (user_id, title, target_date)
                VALUES (?, ?, ?)
                """,
                (current_user.id, title, target_date)
            )

            connection.commit()
            flash("Goal added successfully.", "success")

        connection.close()
        return redirect(url_for("goals"))

    goal_list = connection.execute(
        "SELECT * FROM goals WHERE user_id = ? ORDER BY target_date",
        (current_user.id,)
    ).fetchall()

    connection.close()

    return render_template("goals.html", goals=goal_list)


@app.route("/goals/toggle/<int:goal_id>", methods=["POST"])
@login_required
def toggle_goal(goal_id):

    connection = get_db()

    connection.execute(
        """
        UPDATE goals
        SET completed = CASE WHEN completed = 0 THEN 1 ELSE 0 END
        WHERE id = ? AND user_id = ?
        """,
        (goal_id, current_user.id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("goals"))


@app.route("/goals/delete/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal(goal_id):

    connection = get_db()

    connection.execute(
        "DELETE FROM goals WHERE id = ? AND user_id = ?",
        (goal_id, current_user.id)
    )

    connection.commit()
    connection.close()

    flash("Goal deleted.", "success")

    return redirect(url_for("goals"))


# --------------------------------
# 15. Progress report
# --------------------------------

@app.route("/progress")
@login_required
def progress():

    connection = get_db()

    total_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    completed_tasks = connection.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ? AND status = 'Completed'
        """,
        (current_user.id,)
    ).fetchone()[0]

    total_study_minutes = connection.execute(
        "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    total_goals = connection.execute(
        "SELECT COUNT(*) FROM goals WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    completed_goals = connection.execute(
        "SELECT COUNT(*) FROM goals WHERE user_id = ? AND completed = 1",
        (current_user.id,)
    ).fetchone()[0]

    connection.close()

    completion_percentage = (
        round(completed_tasks / total_tasks * 100)
        if total_tasks > 0 else 0
    )

    return render_template(
        "progress.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        total_study_minutes=total_study_minutes,
        total_goals=total_goals,
        completed_goals=completed_goals,
        completion_percentage=completion_percentage
    )


# --------------------------------
# 16. Page not found
# --------------------------------

@app.errorhandler(404)
def page_not_found(error):

    return render_template("404.html"), 404


# --------------------------------
# 17. Start application
# --------------------------------

if __name__ == "__main__":

    init_db()

    app.run(debug=True)