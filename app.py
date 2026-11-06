import os
import csv
import io
from flask import Response
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(
        db.String(160), unique=True, nullable=False, index=True
    )
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    expenses = db.relationship(
        "Expense",
        backref="owner",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    expense_date = db.Column(
        db.Date, nullable=False, default=date.today
    )
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )


def create_app(test_config=None):
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "expenses.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"

   
    # Expose models on the app for tests and scripts.
    app.User = User
    app.Expense = Expense

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    categories = ["Food", "Transport", "Bills", "Shopping", "Entertainment",
                  "Health", "Education", "Groceries", "Travel", "Other"]
    app.config["EXPENSE_CATEGORIES"] = categories

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            errors = []
            if not name:
                errors.append("Please enter your name.")
            if "@" not in email or "." not in email.split("@")[-1]:
                errors.append("Please enter a valid email address.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password != confirm:
                errors.append("Passwords do not match.")
            if User.query.filter_by(email=email).first():
                errors.append("An account with this email already exists.")
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("register.html", name=name, email=email)
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Welcome back!", "success")
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    def parse_expense_form():
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        amount_text = request.form.get("amount", "").strip()
        date_text = request.form.get("expense_date", "").strip()
        notes = request.form.get("notes", "").strip()
        errors = []
        if not title:
            errors.append("Please enter a description.")
        if category not in categories:
            errors.append("Please select a valid category.")
        try:
            amount = Decimal(amount_text)
            if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99"):
                raise InvalidOperation
            amount = amount.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            amount = None
            errors.append("Enter an amount greater than zero (up to 2 decimal places).")
        try:
            expense_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            expense_date = None
            errors.append("Please select a valid date.")
        if len(notes) > 500:
            errors.append("Notes must be 500 characters or fewer.")
        return title, amount, category, expense_date, notes, errors

    @app.route("/dashboard")
    @login_required
    def dashboard():
        today = date.today()
        month_start = today.replace(day=1)
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
            Expense.expense_date.desc(), Expense.id.desc()
        ).all()
        total = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.user_id == current_user.id
        ).scalar() or 0
        month_total = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.user_id == current_user.id,
            Expense.expense_date >= month_start,
            Expense.expense_date <= today
        ).scalar() or 0
        category_rows = db.session.query(
            Expense.category, func.sum(Expense.amount)
        ).filter(
            Expense.user_id == current_user.id,
            Expense.expense_date >= month_start,
            Expense.expense_date <= today
        ).group_by(Expense.category).all()
        chart_categories = [row[0] for row in category_rows]
        chart_amounts = [float(row[1]) for row in category_rows]
        monthly_rows = db.session.query(
            func.strftime("%Y-%m", Expense.expense_date), func.sum(Expense.amount)
        ).filter(Expense.user_id == current_user.id).group_by(
            func.strftime("%Y-%m", Expense.expense_date)
        ).order_by(func.strftime("%Y-%m", Expense.expense_date)).all()
        monthly_labels = [row[0] for row in monthly_rows if row[0]]
        monthly_amounts = [float(row[1]) for row in monthly_rows if row[0]]
        return render_template(
            "dashboard.html", expenses=expenses, total=float(total),
            month_total=float(month_total), categories=categories,
            chart_categories=chart_categories, chart_amounts=chart_amounts,
            monthly_labels=monthly_labels, monthly_amounts=monthly_amounts,
            today=today.isoformat()
        )

    @app.route("/expenses/export")
    @login_required
    def export_expenses():
        expenses = (
            Expense.query
            .filter_by(user_id=current_user.id)
            .order_by(Expense.expense_date.desc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Title",
            "Amount",
            "Category",
            "Date",
            "Notes",
        ])

        for expense in expenses:
            writer.writerow([
                expense.title,
                expense.amount,
                expense.category,
                expense.expense_date.isoformat(),
                expense.notes or "",
            ])

        response = Response(
            "\ufeff" + output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=expenses.csv"
            },
        )

        return response

    @app.route("/expenses/add", methods=["GET", "POST"])
    @login_required
    def add_expense():
        if request.method == "POST":
            title, amount, category, expense_date, notes, errors = parse_expense_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("expense_form.html", page_title="Add expense",
                                       expense=None, categories=categories, today=date.today().isoformat())
            expense = Expense(title=title,amount=amount,category=category,expense_date=expense_date,notes=notes,user_id=current_user.id,)
            try:
                db.session.add(expense)
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Failed to save a new expense.")
                flash(
                    "We couldn't save your expense. Please try again.",
                    "danger",
                )
                return render_template("expense_form.html",page_title="Add expense",expense=None,categories=categories,today=date.today().isoformat(),
                ), 500

            flash("Expense added successfully.", "success")
            return redirect(url_for("dashboard"))

        return render_template("expense_form.html", page_title="Add expense",
                               expense=None, categories=categories, today=date.today().isoformat())

    @app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_expense(expense_id):
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
        if request.method == "POST":
            title, amount, category, expense_date, notes, errors = parse_expense_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("expense_form.html", page_title="Edit expense",
                                       expense=expense, categories=categories, today=date.today().isoformat())
            expense.title = title
            expense.amount = amount
            expense.category = category
            expense.expense_date = expense_date
            expense.notes = notes

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Failed to update an expense.")

                flash(
                    "We couldn't update your expense. Please try again.",
                    "danger",
                )

                return render_template(
                    "expense_form.html",
                    page_title="Edit expense",
                    expense=expense,
                    categories=categories,
                    today=date.today().isoformat(),
                ), 500

            flash("Expense updated successfully.", "success")
            return redirect(url_for("dashboard"))
        return render_template("expense_form.html", page_title="Edit expense",
                               expense=expense, categories=categories, today=date.today().isoformat())

    @app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
    @login_required
    def delete_expense(expense_id):
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/expenses")
    @login_required
    def list_expenses():
        query = Expense.query.filter_by(user_id=current_user.id)
        category = request.args.get("category", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        search = request.args.get("search", "").strip()
        if category in categories:
            query = query.filter_by(category=category)
        if start_date:
            try:
                query = query.filter(Expense.expense_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
            except ValueError:
                flash("Invalid start date filter.", "warning")
        if end_date:
            try:
                query = query.filter(Expense.expense_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
            except ValueError:
                flash("Invalid end date filter.", "warning")
        if search:
            query = query.filter(Expense.title.ilike(f"%{search}%"))
        sort = request.args.get("sort", "date_desc")

        sort_options = {
            "date_desc": (Expense.expense_date.desc(), Expense.id.desc()),
            "date_asc": (Expense.expense_date.asc(), Expense.id.asc()),
            "amount_desc": (Expense.amount.desc(), Expense.expense_date.desc()),
            "amount_asc": (Expense.amount.asc(), Expense.expense_date.desc()),
        }

        # Calculate the total for all matching expenses
        total = query.with_entities(
            db.func.coalesce(db.func.sum(Expense.amount), 0)
        ).scalar()

        # Get the requested page; default to page 1
        page = request.args.get("page", 1, type=int)

        # Fetch only 10 expenses for the requested page
        pagination = query.order_by(
            *sort_options.get(sort, sort_options["date_desc"])
        ).paginate(
            page=page,
            per_page=2,
            error_out=False
        )

        expenses = pagination.items

        
        return render_template(
            "expenses.html",
            expenses=expenses,
            categories=categories,
            selected_category=category,
            start_date=start_date,
            end_date=end_date,
            search=search,
            filtered_total=total,
            selected_sort=sort,
            pagination=pagination,

        )
    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="The page or expense was not found."), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("error.html", code=500,
                               message="Something went wrong. Please try again."), 500

    with app.app_context():
        db.create_all()

    return app


app = create_app()
