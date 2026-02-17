from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import hashlib
import os
import random
import smtplib
from email.message import EmailMessage

# ---------- APP ----------
app = Flask(__name__)
app.secret_key = "military_secret_key"

# ---------- DATABASE ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")
print("USING DATABASE AT:", DB_PATH)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- EMAIL OTP CONFIG ----------
EMAIL_ADDRESS = "optimindian@gmail.com"
EMAIL_PASSWORD = "hrbepqiyjjaxgpkc"  # app password

def send_otp(email, otp):
    msg = EmailMessage()
    msg.set_content(f"Your booking OTP is: {otp}")
    msg["Subject"] = "Ticket Booking OTP"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

def generate_otp():
    return random.randint(100000, 999999)

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ---------- CREATE TABLES ----------
with get_db() as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            phone TEXT,
            password TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            event_type TEXT,
            seats INTEGER,
            city TEXT,
            event_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            price INTEGER,
            stock INTEGER,
            image TEXT
        )
    """)

# ===================== AUTH =====================

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        identifier = request.form.get("identifier")
        password = hash_password(request.form.get("password"))

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE (email=? OR phone=?) AND password=?",
                (identifier, identifier, password)
            ).fetchone()

        if not user:
            error = "Invalid credentials"
        else:
            session["user"] = user["email"]
            return redirect(url_for("home"))

    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = hash_password(request.form.get("password"))

        otp = generate_otp()
        session["otp"] = str(otp)
        session["otp_purpose"] = "signup"
        session["temp_user"] = (email, phone, password)

        send_otp(email, otp)
        return redirect(url_for("otp"))

    return render_template("register.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    error = None
    if request.method == "POST":
        identifier = request.form.get("identifier")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email=? OR phone=?",
                (identifier, identifier)
            ).fetchone()

        if not user:
            error = "User not found"
            return render_template("forgot.html", error=error)

        otp = generate_otp()
        session["otp"] = str(otp)
        session["otp_email"] = user["email"]
        session["otp_purpose"] = "reset"

        send_otp(user["email"], otp)
        return redirect(url_for("otp"))

    return render_template("forgot.html")

@app.route("/otp", methods=["GET", "POST"])
def otp():
    if request.method == "POST":
        if request.form.get("otp") == session.get("otp"):
            if session.get("otp_purpose") == "signup":
                email, phone, password = session["temp_user"]
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (email, phone, password) VALUES (?, ?, ?)",
                        (email, phone, password)
                    )
                session.clear()
                return redirect(url_for("login"))

            if session.get("otp_purpose") == "reset":
                return redirect(url_for("reset"))

        return "Invalid OTP"

    return render_template("otp.html")

@app.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        new_pass = hash_password(request.form.get("password"))
        email = session.get("otp_email")

        with get_db() as db:
            db.execute(
                "UPDATE users SET password=? WHERE email=?",
                (new_pass, email)
            )

        session.clear()
        return redirect(url_for("login"))

    return render_template("reset.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ===================== HOME =====================
@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("home.html")

# ===================== STATIC =====================
@app.route("/army")
def army():
    return render_template("army.html")

@app.route("/navy")
def navy():
    return render_template("navy.html")

@app.route("/airforce")
def airforce():
    return render_template("airforce.html")

@app.route("/recruitment")
def recruitment():
    return render_template("recruitment.html")



# ===================== BOOKINGS (OTP ADDED) =====================

def start_booking(event_type):
    email = request.form.get("email")
    if not email:
        return "Email is required for OTP", 400

    session["pending_booking"] = {
        "user_email": session["user"],
        "event_type": event_type,
        "seats": request.form.get("seats"),
        "city": request.form.get("city"),
        "event_date": request.form.get("event_date"),
        "email": email
    }

    otp = generate_otp()
    session["booking_otp"] = str(otp)

    send_otp(email, otp)

@app.route("/book/airshow", methods=["GET", "POST"])
def book_air():
    if request.method == "POST":
        resp = start_booking("Air Show")
        if resp:
            return resp
        return redirect(url_for("booking_otp"))
    return render_template("booking.html", event_name="Air Force Air Show")


@app.route("/book/army-parade", methods=["GET", "POST"])
def book_army():
    if request.method == "POST":
        resp = start_booking("Army Parade")
        if resp:
            return resp
        return redirect(url_for("booking_otp"))
    return render_template("booking.html", event_name="Indian Army Parade")


@app.route("/book/naval-show", methods=["GET", "POST"])
def book_navy():
    if request.method == "POST":
        resp = start_booking("Naval Show")
        if resp:
            return resp
        return redirect(url_for("booking_otp"))
    return render_template("booking.html", event_name="Indian Navy Show")



@app.route("/booking-otp", methods=["GET", "POST"])
def booking_otp():
    if request.method == "POST":
        if request.form.get("otp") == session.get("booking_otp"):
            data = session.get("pending_booking")

            with get_db() as db:
                db.execute("""
                    INSERT INTO bookings
                    (user_email, event_type, seats, city, event_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    data["user_email"],
                    data["event_type"],
                    data["seats"],
                    data["city"],
                    data["event_date"]
                ))

            session.pop("pending_booking")
            session.pop("booking_otp")
            return redirect(url_for("my_bookings"))

        return "Invalid OTP"

    return render_template("booking_otp.html")

@app.route("/my-bookings")
def my_bookings():
    with get_db() as db:
        bookings = db.execute(
            "SELECT * FROM bookings WHERE user_email=?",
            (session["user"],)
        ).fetchall()
    return render_template("my_bookings.html", bookings=bookings)

# ===================== STORE + CART =====================
@app.route("/store")
def store():
    with get_db() as db:
        products = db.execute("SELECT * FROM products").fetchall()
    return render_template("store.html", products=products)

@app.route("/add-to-cart/<int:pid>")
def add_to_cart(pid):
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + 1
    session["cart"] = cart
    return redirect(url_for("store"))

@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    items = []
    total = 0

    with get_db() as db:
        for pid, qty in cart.items():
            p = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if p:
                subtotal = p["price"] * qty
                total += subtotal
                items.append((p, qty, subtotal))

    return render_template("cart.html", items=items, total=total)

@app.route("/remove-from-cart/<int:pid>")
def remove_from_cart(pid):
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/clear-cart")
def clear_cart():
    session.pop("cart", None)
    return redirect(url_for("cart"))
@app.route("/test-css")
def test_css():
    return """
    <html>
    <head>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1 style="color:red">If background is visible, CSS works</h1>
        <div class="login-card">CSS TEST</div>
    </body>
    </html>
    """


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
