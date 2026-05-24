from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change in production

# Mock database for now (will be replaced with SQLite)
users_db = {}
expenses_db = {}
balance_db = {}  # Store balance for each user


# ------------------------------------------------------------------ #
# Decorators & Helper Functions                                       #
# ------------------------------------------------------------------ #

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if not email or not password or not confirm_password:
            return render_template("register.html", error="All fields required")
        
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")
        
        if email in users_db:
            return render_template("register.html", error="Email already registered")
        
        # Store user (in real app, hash password and use database)
        users_db[email] = {"password": password}
        return redirect(url_for('login'))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            return render_template("login.html", error="Email and password required")
        
        if email not in users_db or users_db[email]["password"] != password:
            return render_template("login.html", error="Invalid email or password")
        
        session['user_id'] = email
        return redirect(url_for('dashboard'))
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing'))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user_id = session['user_id']
    user_expenses = expenses_db.get(user_id, [])
    
    # Handle balance update
    if request.method == "POST":
        balance = request.form.get("balance")
        if balance:
            try:
                balance_db[user_id] = float(balance)
            except ValueError:
                pass
    
    # Get current balance
    total_balance = balance_db.get(user_id, 0)
    total_expenses = sum(exp['amount'] for exp in user_expenses)
    remaining_balance = total_balance - total_expenses
    transaction_count = len(user_expenses)
    
    return render_template("dashboard.html",
                         expenses=user_expenses,
                         total_balance=total_balance,
                         total_expenses=total_expenses,
                         remaining_balance=remaining_balance,
                         transaction_count=transaction_count)


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        description = request.form.get("description")
        amount = request.form.get("amount")
        category = request.form.get("category")
        date = request.form.get("date")
        notes = request.form.get("notes")
        
        if not description or not amount or not category or not date:
            return render_template("add_expense.html", error="All fields required")
        
        user_id = session['user_id']
        
        if user_id not in expenses_db:
            expenses_db[user_id] = []
        
        expense = {
            "id": len(expenses_db[user_id]) + 1,
            "description": description,
            "amount": float(amount),
            "category": category,
            "date": date,
            "notes": notes
        }
        
        expenses_db[user_id].append(expense)
        return redirect(url_for('dashboard'))
    
    # Set today's date as default
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("add_expense.html", today=today)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    user_id = session['user_id']
    user_expenses = expenses_db.get(user_id, [])
    
    expense = next((exp for exp in user_expenses if exp['id'] == id), None)
    
    if not expense:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        expense['description'] = request.form.get("description")
        expense['amount'] = float(request.form.get("amount"))
        expense['category'] = request.form.get("category")
        expense['date'] = request.form.get("date")
        expense['notes'] = request.form.get("notes")
        
        return redirect(url_for('dashboard'))
    
    return render_template("add_expense.html", expense=expense, is_edit=True)


@app.route("/expenses/<int:id>/delete")
@login_required
def delete_expense(id):
    user_id = session['user_id']
    user_expenses = expenses_db.get(user_id, [])
    
    # Check if this is the last expense
    is_last_expense = len(user_expenses) == 1
    
    # Delete the expense
    expenses_db[user_id] = [exp for exp in user_expenses if exp['id'] != id]
    
    # If it was the last expense, redirect to balance update page
    if is_last_expense:
        return redirect(url_for('update_balance_after_delete'))
    
    return redirect(url_for('dashboard'))


@app.route("/balance/update-after-delete", methods=["GET", "POST"])
@login_required
def update_balance_after_delete():
    user_id = session['user_id']
    current_balance = balance_db.get(user_id, 0)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "reset":
            # Reset balance to 0
            balance_db[user_id] = 0
        elif action == "update":
            # Update with new balance
            new_balance = request.form.get("new_balance")
            if new_balance:
                try:
                    balance_db[user_id] = float(new_balance)
                except ValueError:
                    pass
        
        return redirect(url_for('dashboard'))
    
    return render_template("update_balance.html", current_balance=current_balance)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
