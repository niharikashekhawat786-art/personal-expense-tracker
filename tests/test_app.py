import unittest
from app import create_app, db


class ExpenseTrackerTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def register_and_login(self, email="test@example.com"):
        response = self.client.post("/register", data={
            "name": "Test User", "email": email,
            "password": "safe-pass-123", "confirm_password": "safe-pass-123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/login", data={
            "email": email, "password": "safe-pass-123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_register_login_add_expense(self):
        self.register_and_login()
        response = self.client.post("/expenses/add", data={
            "title": "Lunch", "amount": "120.50", "category": "Food",
            "expense_date": "2026-10-22", "notes": "Test entry"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lunch", response.data)
        self.assertIn(b"120.50", response.data)

    def test_invalid_amount_is_rejected(self):
        self.register_and_login()
        response = self.client.post("/expenses/add", data={
            "title": "Invalid", "amount": "-5", "category": "Food",
            "expense_date": "2026-10-22", "notes": ""
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter an amount greater than zero", response.data)

    def test_user_cannot_view_another_users_expense(self):
        self.register_and_login()
        response = self.client.post("/expenses/add", data={
            "title": "Private item", "amount": "50", "category": "Other",
            "expense_date": "2026-10-22", "notes": ""
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            expense_id = self.app.Expense.query.filter_by(title="Private item").first().id
        self.client.post("/logout", follow_redirects=True)
        self.register_and_login("other@example.com")
        response = self.client.get(f"/expenses/{expense_id}/edit")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
