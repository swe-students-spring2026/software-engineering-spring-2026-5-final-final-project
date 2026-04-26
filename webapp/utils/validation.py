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
