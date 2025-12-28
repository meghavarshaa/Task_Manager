from flask import Flask, render_template, request, redirect, url_for, flash, session
from db_config import get_connection
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super-secret-key"  # change in production


def fetch_tasks():
    if "user_id" not in session:
        return []
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks ORDER BY due_date IS NULL, due_date, priority DESC;")
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return tasks


def fetch_summary():
    if "user_id" not in session:
        return {"pending": 0, "completed": 0, "total": 0}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            SUM(CASE WHEN is_completed = 0 THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS completed,
            COUNT(*) AS total
        FROM tasks;
    """)
    summary = cursor.fetchone()
    cursor.close()
    conn.close()
    return summary

from datetime import date

from datetime import date

@app.route("/", methods=["GET"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "due_date")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch unique categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM tasks ORDER BY category")
    categories = [row["category"] for row in cursor.fetchall()]

    # Analytics: tasks by category
    cursor.execute("SELECT category, COUNT(*) AS count FROM tasks GROUP BY category")
    cat_rows = cursor.fetchall()
    category_labels = [row["category"] or "Uncategorized" for row in cat_rows]
    category_counts = [row["count"] for row in cat_rows]

    # Analytics: tasks by priority
    cursor.execute("SELECT priority, COUNT(*) AS count FROM tasks GROUP BY priority")
    pri_rows = cursor.fetchall()
    priority_labels = [row["priority"] for row in pri_rows]
    priority_counts = [row["count"] for row in pri_rows]

    # Main task list with search / category / sort
    if search:
        cursor.execute(
            f"""
            SELECT * FROM tasks
            WHERE title LIKE %s
            ORDER BY {sort} IS NULL, {sort}, priority DESC
            """,
            (f"%{search}%",),
        )
    elif category:
        cursor.execute(
            f"""
            SELECT * FROM tasks
            WHERE category = %s
            ORDER BY {sort} IS NULL, {sort}, priority DESC
            """,
            (category,),
        )
    else:
        cursor.execute(
            f"""
            SELECT * FROM tasks
            ORDER BY {sort} IS NULL, {sort}, priority DESC
            """
        )

    tasks = cursor.fetchall()
    cursor.close()
    conn.close()

    summary = fetch_summary()

    return render_template(
        "index.html",
        tasks=tasks,
        summary=summary,
        search=search,
        category=category,
        categories=categories,
        now=date.today(),
        sort=sort,
        category_labels=category_labels,
        category_counts=category_counts,
        priority_labels=priority_labels,
        priority_counts=priority_counts,
    )



@app.route("/add", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return redirect(url_for("login"))
    title = request.form.get("title")
    description = request.form.get("description")
    category = request.form.get("category")
    priority = request.form.get("priority")
    due_date_str = request.form.get("due_date")

    if not title:
        flash("Title is required", "danger")
        return redirect(url_for("index"))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "danger")
            return redirect(url_for("index"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tasks (title, description, category, priority, due_date)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (title, description, category, priority, due_date),
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Task added successfully", "success")
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET is_completed = NOT is_completed WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Task updated", "info")
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Task deleted", "warning")
    return redirect(url_for("index"))


@app.route("/edit/<int:task_id>", methods=["POST"])
def edit_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    title = request.form.get("title")
    description = request.form.get("description")
    category = request.form.get("category")
    priority = request.form.get("priority")
    due_date_str = request.form.get("due_date")

    if not title:
        flash("Title is required", "danger")
        return redirect(url_for("index"))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "danger")
            return redirect(url_for("index"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tasks
        SET title=%s, description=%s, category=%s, priority=%s, due_date=%s
        WHERE id=%s
        """,
        (title, description, category, priority, due_date, task_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Task updated successfully", "success")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_hash = generate_password_hash(password)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration successful", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("Login successful", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
