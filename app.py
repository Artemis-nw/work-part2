
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import get_db_connection

app = Flask(__name__)

app.secret_key = "storyverse-development-secret"


@app.route("/")
def home():
    search_query = request.args.get("q", "").strip()

    connection = get_db_connection()

    try:
        stories = connection.execute(
            """
            SELECT
                s.id,
                s.title,
                s.description,
                s.genre,
                s.tags,
                s.cover,
                s.status,
                s.created_at,
                u.username AS author
            FROM stories AS s
            JOIN users AS u ON u.id = s.author_id
            WHERE s.status IN ('ongoing', 'completed')
              AND EXISTS (
                  SELECT 1
                  FROM chapters AS c
                  WHERE c.story_id = s.id
                    AND c.status = 'published'
              )
              AND (
                  ? = ''
                  OR s.title LIKE ?
                  OR s.description LIKE ?
                  OR s.genre LIKE ?
                  OR s.tags LIKE ?
                  OR u.username LIKE ?
              )
            ORDER BY s.created_at DESC
            LIMIT 24
            """,
            (
                search_query,
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%"
            )
        ).fetchall()
    finally:
        connection.close()

    return render_template(
        "index.html",
        stories=stories,
        search_query=search_query
    )


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check that every field has been filled in.
        if not username or not email or not password or not confirm_password:
            flash("Please fill in every field.")
            return render_template("register.html")

        if len(username) > 30:
            flash("Username must be 30 characters or fewer.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return render_template("register.html")

        if password != confirm_password:
            flash("The passwords do not match.")
            return render_template("register.html")

        connection = get_db_connection()

        try:
            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE username = ? OR email = ?
                """,
                (username, email)
            ).fetchone()

            if existing_user:
                flash("That username or email is already registered.")
                return render_template("register.html")

            password_hash = generate_password_hash(password)

            connection.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (username, email, password_hash)
            )

            connection.commit()

        finally:
            connection.close()

        flash("Your account has been created. You can now log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter your username and password.")
            return render_template("login.html")

        connection = get_db_connection()

        try:
            user = connection.execute(
                """
                SELECT id, username, password_hash
                FROM users
                WHERE username = ?
                """,
                (username,)
            ).fetchone()
        finally:
            connection.close()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            flash("Invalid username or password.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        flash("Welcome back, " + user["username"] + "!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/writing")
def writing_dashboard():
    if "user_id" not in session:
        flash("Please log in to access your writing dashboard.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        stories = connection.execute(
            """
            SELECT
                s.id,
                s.title,
                s.genre,
                s.status,
                s.created_at,
                (
                    SELECT COUNT(*)
                    FROM chapters AS c
                    WHERE c.story_id = s.id
                ) AS chapter_count
            FROM stories AS s
            WHERE s.author_id = ?
            ORDER BY s.created_at DESC, s.id DESC
            """,
            (session["user_id"],)
        ).fetchall()
    finally:
        connection.close()

    return render_template(
        "writing_dashboard.html",
        stories=stories
    )


@app.route("/writing/new", methods=["GET", "POST"])
def create_story():
    if "user_id" not in session:
        flash("Please log in before creating a story.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        genre = request.form.get("genre", "").strip()
        tags = request.form.get("tags", "").strip()

        if not title:
            flash("Please enter a story title.")
            return render_template("create_story.html")

        if len(title) > 150:
            flash("The title must be 150 characters or fewer.")
            return render_template("create_story.html")

        connection = get_db_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO stories (
                    author_id,
                    title,
                    description,
                    genre,
                    tags,
                    status
                )
                VALUES (?, ?, ?, ?, ?, 'draft')
                """,
                (
                    session["user_id"],
                    title,
                    description,
                    genre,
                    tags
                )
            )

            story_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        flash("Your story draft has been created.", "success")
        return redirect(
            url_for("edit_chapter", story_id=story_id)
        )

    return render_template("create_story.html")


@app.route("/writing/<int:story_id>/chapters/new", methods=["GET", "POST"])
def create_chapter(story_id):
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        story = connection.execute(
            """
            SELECT id, title
            FROM stories
            WHERE id = ? AND author_id = ?
            """,
            (story_id, session["user_id"])
        ).fetchone()

        if story is None:
            flash("Story not found or you do not have permission.")
            return redirect(url_for("writing_dashboard"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()

            if not title or not content:
                flash("Please enter both a chapter title and its content.")
                return render_template(
                    "create_chapter.html",
                    story=story
                )

            next_number = connection.execute(
                """
                SELECT COALESCE(MAX(chapter_number), 0) + 1
                AS next_number
                FROM chapters
                WHERE story_id = ?
                """,
                (story_id,)
            ).fetchone()["next_number"]

            connection.execute(
                """
                INSERT INTO chapters (
                    story_id, chapter_number, title, content, status
                )
                VALUES (?, ?, ?, ?, 'draft')
                """,
                (story_id, next_number, title, content)
            )

            connection.commit()
            flash("Chapter draft saved successfully.", "success")
            return redirect(url_for("writing_dashboard"))

    finally:
        connection.close()

    return render_template("create_chapter.html", story=story)


@app.route("/writing/<int:story_id>")
def view_story(story_id):
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        story = connection.execute(
            """
            SELECT id, title, description, genre, status
            FROM stories
            WHERE id = ? AND author_id = ?
            """,
            (story_id, session["user_id"])
        ).fetchone()

        if story is None:
            flash("Story not found.")
            return redirect(url_for("writing_dashboard"))

        chapters = connection.execute(
            """
            SELECT id, chapter_number, title, status, updated_at
            FROM chapters
            WHERE story_id = ?
            ORDER BY chapter_number
            """,
            (story_id,)
        ).fetchall()
    finally:
        connection.close()

    return render_template(
        "view_story.html",
        story=story,
        chapters=chapters
    )


if __name__ == "__main__":
    app.run(debug=True)