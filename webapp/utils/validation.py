from werkzeug.security import check_password_hash

def validate_signup(data, users_collection):
    """
    This function validates the signup form data. It checks for:
    - Required fields are filled out
    - Password and confirm password match
    - Email is valid and matches confirm email
    - Email is not already in use
    """
    required_fields = [
        "email",
        "confirm_email",
        "password",
        "confirm_password",
        "first_name",
        "last_name",
        "age",
        "neighborhood",
    ]

    for field in required_fields:
        if not data.get(field):
            return "Please fill out all required fields."

    if data["password"] != data["confirm_password"]:
        return "Passwords do not match."

    if "@" not in data["email"]:
        return "Please enter a valid email."
    
    if data["email"] != data["confirm_email"]:
        return "Emails do not match."

    if users_collection.find_one({"email": data["email"]}):
        return "An account with this email already exists."

    return None

def validate_login(data, users_collection):
    """
    Validate login form data.
    Returns: (error, user_data)
    """

    # Required fields
    if not data.get("email") or not data.get("password"):
        return "Please enter email and password.", None

    # Check user exists
    user = users_collection.find_one({"email": data["email"]})
    if not user:
        return "No account found with that email.", None

    # Check password
    if not check_password_hash(user["password_hash"], data["password"]):
        return "Incorrect password.", None

    return None, user

def validate_event(data):
    """
    Validate event creation form data.
    Checks for:
    - Required fields are filled out
    - Capacity is a number and at least 3
    - No more than 3 tags
    Returns: error message or None if valid
    """
    required_fields = ["title", "datetime", "capacity", "description"]

    for field in required_fields:
        if not data.get(field):
            return f"{field} is required."

    if int(data["capacity"]) < 3:
        return "Capacity must be at least 3."

    if "tags" in data and len(data["tags"]) > 3:
        return "You can select up to 3 tags only."

    return None
