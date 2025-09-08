from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from .models import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import math

main = Blueprint('main', __name__)


# Home page
@main.route('/')
def home():
    return render_template('index.html')

# Products page
@main.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, unit, image_url FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('products.html', products=products)

# About page
@main.route('/about')
def about():
    return render_template('about.html')

# Contact page
@main.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        conn = get_db_connection()
        conn.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)",
                     (name, email, message))
        conn.commit()
        conn.close()

        return redirect(url_for("messages"))  # redirect to messages page

    return render_template("contact.html")

#Send message from contact form

@main.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # For now, just flash confirmation
    flash(f"Thanks {name}, we received your message: '{message}'")

    # Later you could store it in DB or send email
    return redirect(url_for('main.contact'))

# Register route
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        # check if email already exists
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        existing = cursor.fetchone()
        if existing:
            flash("Email already registered. Please log in.")
            conn.close()
            return redirect(url_for('main.login'))

        # save new user with hashed password
        hashed_pw = generate_password_hash(password)
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (name, email, hashed_pw))
        conn.commit()
        conn.close()

        flash("You are now Registered! Please log in.")
        return redirect(url_for('main.login'))

    return render_template('register.html')


# Login page
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for('main.products'))
        else:
            flash("Invalid email or password.")

    return render_template('login.html')     

# Logout
@main.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('main.home'))

# Display cart
@main.route('/cart')
def cart():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.")
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cart.id AS cart_id, products.name, products.price, products.unit, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (user_id,))
    cart_items = cursor.fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

# Add to cart
@main.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.")
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if item already in cart
    cursor.execute("SELECT id, quantity FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
    existing = cursor.fetchone()
    if existing:
        # Update quantity
        cursor.execute("UPDATE cart SET quantity=? WHERE id=?", (existing['quantity'] + 1, existing['id']))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, 1))
    conn.commit()
    conn.close()
    flash(f"We put your goods in the basket!")
    return redirect(url_for('main.products'))

# Remove from cart
@main.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.")
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cart_id, user_id))
    conn.commit()
    conn.close()
    flash("YOU HAVE EMPTIED YOUR  BASKET.")
    return redirect(url_for('main.cart'))

@main.route('/messages')
def messages():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # messages per page
    offset = (page - 1) * per_page

    conn = get_db_connection()
    messages = conn.execute(
        "SELECT * FROM messages ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()

    total_pages = (total_messages + per_page - 1) // per_page

    return render_template(
        'messages.html',
        messages=messages,
        page=page,
        total_pages=total_pages
    )


@main.route('/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    flash("You deleted that Message!")
    return redirect(url_for('main.messages'))

# Checkout page
@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.")
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch cart items
    cursor.execute("""
        SELECT products.name, products.price, products.unit, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (user_id,))
    cart_items = cursor.fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)

    if request.method == 'POST':
        # Here you could handle "order placement"
        cursor.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

        flash("✅ You agreed, we are bringing your goods. Thank you!")
        return redirect(url_for('main.products'))

    conn.close()
    return render_template('checkout.html', cart_items=cart_items, total=total)
