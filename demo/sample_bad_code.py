"""Sample file with intentionally bad code, used to demonstrate the AI Code Review Bot."""


API_KEY = "sk-test-1234567890abcdef"  # hardcoded credential


def get_user(user_id):
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"  # SQL injection
    return query


def divide(a, b):
    return a / b  # no zero-division check


def calculate_discount(price, discount_percent):
    return price - (price * 37 / 100)  # magic number, ignores the discount_percent argument
