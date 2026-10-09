from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from io import BytesIO
import MySQLdb.cursors
from reportlab.lib.pagesizes import letter
from werkzeug.utils import secure_filename
import re
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import io
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors





app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'  # Required for session handling

# Create uploads folder path
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Add to Flask config
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'online_pharmacy'
mysql = MySQL(app)

def is_admin():
    return session.get('loggedin') and session.get('role') == 'admin'

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Login Logic
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'SELECT * FROM users WHERE email = %s AND password = %s',
        (email, password)
    )
    user = cursor.fetchone()

    if user:
        session['loggedin'] = True
        session['user_id'] = user['id'] 
        session['user_name'] = user['name']
        session['email'] = user['email']
        session['role'] = user['role']
        flash('Login Successful!', 'success')

        if session['role'] == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('home'))
    else:
        flash('Invalid email or password!', 'danger')
        return redirect(url_for('home'))

# Signup Logic
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    account = cursor.fetchone()

    if account:
        flash('Email already exists!', 'danger')
    elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash('Invalid email address!', 'danger')
    elif not name or not password or not email:
        flash('Please fill out all fields!', 'warning')
    else:
        cursor.execute(
            'INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
            (name, email, password, 'user')
        )
        mysql.connection.commit()
        flash('Signup successful! Please log in.', 'success')

    return redirect(url_for('home'))

# Dedicated Admin Route
@app.route('/admin')
def admin():
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

# Admin orders page
@app.route('/admin/orders')
def admin_orders():
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    cursor.close()

    print("DEBUG ORDERS:", orders)  # Optional: check console
    return render_template('admin_orders.html', orders=orders)

# Admin users page
@app.route('/admin/users')
def admin_users():   # ✅ Keep this name, since templates use url_for('admin_users')
    if 'role' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        # Fetch all users
        cursor.execute("SELECT id, name, email, role FROM users")
        users = cursor.fetchall()
        cursor.close()
        return render_template('admin_users.html', users=users)
    else:
        flash("Access denied!")
        return redirect(url_for('home'))


# Admin categories page
@app.route('/admin/categories')
def admin_categories():
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    # Fetch categories from DB here if needed
    return render_template('admin_categories.html')

# Show all products
@app.route('/admin/products')
def admin_products():
    if not is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get all products
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    # Get all categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    
    return render_template('admin_products.html', products=products, categories=categories)


# Add product
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    categories = [
        'Medicines', 'Wellness', 'Healthcare Devices', 'Sports Nutrition', 
        'Diabetes Essential', 'Baby & Mother', 'Monsoon Care', 
        'Vitamins & Supplements', 'Ayurvedic', 'Health Food & Drinks', 
        'Mobility & Elderly Care', 'Heart Care'
    ]

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']
        stock = request.form['stock']

        # Handle file upload
        file = request.files['image_file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
            image_url = f"uploads/{filename}"  # relative path for templates
        else:
            image_url = None  # optional default image

        # Insert into database
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO products (name, description, category, price, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, description, category, price, stock, image_url))
        mysql.connection.commit()
        cursor.close()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))

    return render_template('add_product.html', categories=categories)


# Edit product
@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not is_admin():
        flash("Access denied!", "danger")
        return redirect(url_for("home"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch the product
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()

    # Fetch all categories
    cursor.execute("SELECT name FROM categories")
    categories = [row['name'] for row in cursor.fetchall()]

    cursor.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("admin_products"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        category = request.form["category"]
        price = request.form["price"]
        stock = request.form["stock"]

        # Handle image upload
        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            image_url = f"uploads/{filename}"
        else:
            image_url = product["image_url"]  # Keep old image

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE products 
            SET name=%s, description=%s, category=%s, price=%s, stock=%s, image_url=%s
            WHERE id=%s
        """, (name, description, category, price, stock, image_url, product_id))
        mysql.connection.commit()
        cursor.close()

        flash("Product updated successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template("admin_edit_product.html", product=product, categories=categories)


# Delete product
@app.route("/admin/products/delete/<int:product_id>")
def delete_product(product_id):
    if not is_admin():
        flash("Access denied!", "danger")
        return redirect(url_for("home"))

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    mysql.connection.commit()
    cursor.close()

    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_products"))


@app.route('/admin/dashboard')
def admin_dashboard():
    # Optional: Check if the logged-in user is admin
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    else:
        flash("Access denied! Admins only.")
        return redirect(url_for('index'))



@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/shop')
def shop():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE is_active = 1")
    products = cursor.fetchall()
    cursor.close()
    return render_template('shop.html', products=products)


# Category Page
@app.route('/category/<name>')
def category(name):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE category=%s AND is_active=1", (name,))
    products = cursor.fetchall()
    cursor.close()
    return render_template("category.html", products=products, category=name)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

# 404 Handler
@app.errorhandler(404)
def not_found(e):
    return "<h2>Page not found</h2>", 404

@app.route("/medicine")
def medicine():
    products = [
        {"id": 1, "name": "Paracetamol", "price": 50},
        {"id": 2, "name": "Amoxicillin", "price": 120},
        {"id": 3, "name": "Cough Syrup", "price": 90},
        {"id": 4, "name": "Vitamin C Tablets", "price": 150}
    ]
    return render_template("medicine.html", products=products)

# 🛒 Add to Cart
# 🛒 Add to Cart
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    # Check if user is logged in
    if "user_id" not in session:
        return jsonify({"error": "login_required"}), 401  # HTTP 401 Unauthorized

    data = request.get_json()
    product_id = str(data.get("product_id"))  # Ensure string key
    product_name = data.get("product_name")
    price = float(data.get("price"))          # Price as float
    stock = int(data.get("stock"))
    
    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    # If product exists in cart, increase quantity
    if product_id in cart:
        if cart[product_id]["quantity"] < stock:
            cart[product_id]["quantity"] += 1
    else:
        cart[product_id] = {
            "name": product_name,
            "price": price,
            "quantity": 1,
            "stock": stock
        }

    session["cart"] = cart
    session["cart_count"] = sum(item["quantity"] for item in cart.values())
    session.modified = True

    return jsonify({
        "cart_count": session["cart_count"],
        "quantity": cart[product_id]["quantity"]
    })



# 🛒 Remove from Cart
@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    data = request.get_json()
    product_id = data.get("product_id")
    if "cart" in session and product_id in session["cart"]:
        session["cart"].pop(product_id)
        session["cart_count"] = sum(item["quantity"] for item in session["cart"].values())
        session.modified = True
    return jsonify({"cart_count": session.get("cart_count", 0)})

@app.route("/clear_cart", methods=["POST"])
def clear_cart():
    session.pop("cart", None)
    session["cart_count"] = 0
    session.modified = True
    return "", 204


#decrement
@app.route("/decrement_cart", methods=["POST"])
def decrement_cart():
    data = request.get_json()
    product_id = str(data.get("product_id"))

    if "cart" in session and product_id in session["cart"]:
        cart = session["cart"]
        cart[product_id]["quantity"] -= 1
        if cart[product_id]["quantity"] <= 0:
            del cart[product_id]  # Remove product if quantity 0

        session["cart"] = cart
        session["cart_count"] = sum(item["quantity"] for item in cart.values())
        session.modified = True

        quantity = cart[product_id]["quantity"] if product_id in cart else 0
        return jsonify({"cart_count": session["cart_count"], "quantity": quantity})

    return jsonify({"cart_count": session.get("cart_count", 0), "quantity": 0})



# 🛒 Cart Page
@app.route("/cart")
def cart():
    cart_items = session.get("cart", [])
    return render_template("cart.html", cart_items=cart_items)



@app.route('/admin/users/delete/<int:user_id>')
def delete_user(user_id):
    if 'role' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        mysql.connection.commit()
        cursor.close()
        flash("User deleted successfully!")
        return redirect(url_for('admin_users'))
    else:
        flash("Access denied!")
        return redirect(url_for('index'))


@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'role' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            role = request.form['role']
            cursor.execute("UPDATE users SET name=%s, email=%s, role=%s WHERE id=%s",
                           (name, email, role, user_id))
            mysql.connection.commit()
            cursor.close()
            flash("User updated successfully!")
            return redirect(url_for('admin_users'))
        else:
            cursor.execute("SELECT id, name, email, role FROM users WHERE id=%s", (user_id,))
            user = cursor.fetchone()
            cursor.close()
            return render_template('edit_users.html', user=user)
    else:
        flash("Access denied!")
        return redirect(url_for('index'))


@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']

            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password, role)
            )
            mysql.connection.commit()
            cursor.close()
            flash("User added successfully!", "success")
            return redirect(url_for('manage_users'))

        # GET request → show add_user form
        return render_template('add_user.html')
    else:
        flash("Access denied!", "danger")
        return redirect(url_for('index'))

@app.route('/orders')
def orders():
    if not is_admin():
        flash("Access denied!", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    cursor.close()

    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/orders/update/<int:order_id>/<status>')
def update_order_status(order_id, status):
    if not is_admin():
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    mysql.connection.commit()
    cursor.close()
    flash(f"Order #{order_id} status updated to {status}!", "success")
    return redirect(url_for('admin_orders'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    if 'cart' not in session or not session['cart']:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('shop'))

    cursor = mysql.connection.cursor()

    # Loop through all items in cart
    for product_id, item in session['cart'].items():
        cursor.execute("""
            INSERT INTO orders (customer_name, product, quantity, total_price, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session['user_name'],   # customer name
            item['name'],           # product name
            item['quantity'],       # quantity
            item['price'] * item['quantity'],  # total price
            'Pending'               # default status
        ))

    mysql.connection.commit()
    cursor.close()

    # Clear the cart after checkout
    session.pop('cart', None)
    session['cart_count'] = 0
    session.modified = True

    flash("Payment successful! Your order has been placed.", "success")
    return redirect(url_for('user_orders'))  # optional: show user their orders



@app.route('/my_orders')
def user_orders():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('home'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders WHERE customer_name=%s", (session['user_name'],))
    orders = cursor.fetchall()
    cursor.close()

    return render_template('user_orders.html', orders=orders)

@app.route("/place_order", methods=["POST"])
def place_order():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first!"}), 401

    if "cart" not in session or not session["cart"]:
        return jsonify({"success": False, "message": "Cart is empty!"})

    cart_dict = session["cart"]
    total = 0
    cursor = mysql.connection.cursor()

    try:
        for product_key, item in cart_dict.items():
            # Extract product ID from the session key (assumes keys like 'product_1')
            product_id = product_key.split("_")[-1]  

            # Get current stock from DB
            cursor.execute("SELECT stock FROM products WHERE id=%s", (product_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"success": False, "message": f"Product {item['name']} not found."})
            
            stock = result[0]

            # Check stock availability
            if stock < item["quantity"]:
                return jsonify({
                    "success": False,
                    "message": f"Not enough stock for {item['name']}. Available: {stock}"
                })

            # Reduce stock
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item["quantity"], product_id)
            )

            # Add to total
            total += float(item["price"]) * item["quantity"]

        # Commit all changes
        mysql.connection.commit()

        # Save last order in session for receipt
        session['last_order'] = {
            "cart": list(cart_dict.values()),
            "total": total,
            "name": session.get("user_name", "Not Provided"),
            "email": session.get("email", "Not Provided")
        }

        # Now clear the cart
        session.pop("cart", None)
        session['cart_count'] = 0
        session.modified = True

        return jsonify({
            "success": True,
            "name": session.get("user_name", "Not Provided"),
            "email": session.get("email", "Not Provided"),
            "cart": list(cart_dict.values()),
            "total": total,
            "message": "Order placed successfully!"
        })

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"success": False, "message": str(e)})

    finally:
        cursor.close()



@app.route("/download_receipt_txt")
def download_receipt_txt():
    if "last_order" not in session:
        return "No recent order to generate receipt.", 400

    order = session["last_order"]
    cart_items = order["cart"]
    total = order["total"]
    name = order["name"]
    email = order["email"]

    lines = []
    lines.append("=== PharmaCare Receipt ===\n")
    lines.append(f"Name: {name}")
    lines.append(f"Email: {email}\n")
    lines.append(f"{'Medicine':<25} {'Qty':<5} {'Unit Price':<12} {'Subtotal':<10}")
    lines.append("-"*60)

    for item in cart_items:
        item_name = item.get("name", "Unknown")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        subtotal = qty * price
        lines.append(f"{item_name:<25} {qty:<5} {price:<12.2f} {subtotal:<10.2f}")

    lines.append("-"*60)
    lines.append(f"{'':<40}Total Amount : {total:.2f}\n")
    lines.append("Thank you for shopping with PharmaCare!")

    receipt_text = "\n".join(lines)

    from flask import Response
    return Response(
        receipt_text,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=receipt.txt"}
    )


if __name__ == '__main__':
    app.run(debug=True)
