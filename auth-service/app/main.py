"""Auth Service for CatCh.

This service owns email verification and JWT creation. It only describes the
authenticated user's role; gameplay permissions are enforced by downstream
services.
"""

from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal, Optional
import os
import secrets
import smtplib

import jwt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your-email@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

UserRole = Literal["kitten", "cat"]

# In-memory template store. Replace with Redis or MongoDB TTL collection later.
verification_codes: dict[str, dict] = {}


class SendVerificationEmailRequest(BaseModel):
    """Request body for creating and sending a verification code."""

    email: EmailStr
    role: UserRole = Field(default="kitten")


class VerifyEmailRequest(BaseModel):
    """Request body for validating an email verification code."""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    role: UserRole = Field(default="kitten")


class AuthResponse(BaseModel):
    """Authentication response returned after a successful login."""

    token: str
    user_id: str
    email: EmailStr
    role: UserRole
    expires_at: str
    token_system_enabled: bool
    permissions: list[str]


class TokenRefreshRequest(BaseModel):
    """Request body for refreshing an existing JWT."""

    token: str


class VerifyTokenRequest(BaseModel):
    """Request body for checking whether a JWT is valid."""

    token: str


class TokenValidationResponse(BaseModel):
    """Response body for token validation requests."""

    valid: bool
    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    expires_at: Optional[str] = None
    token_system_enabled: bool = False
    permissions: list[str] = []


def permissions_for_role(role: UserRole) -> list[str]:
    """Return the permission names granted to a CatCh user role."""

    if role == "cat":
        return [
            "create_public_pond",
            "create_private_pond",
            "manage_pond_problems",
            "send_room_code_invites",
            "manage_assignments",
        ]
    return [
        "join_pond",
        "solve_problem",
        "earn_fishing_chance",
        "fish",
        "manage_aquarium",
        "use_marketplace",
        "use_cat_can_tokens",
        "vote_on_public_pond",
    ]


def token_system_enabled(role: UserRole) -> bool:
    """Return whether a CatCh role participates in Cat Can Tokens."""

    return role == "kitten"


def send_verification_email(
    to_email: str, verification_code: str, role: UserRole
) -> bool:
    """Send a CatCh login code. Returns False when SMTP is not configured."""
    if not SENDER_PASSWORD:
        print("SMTP password is not configured; skipping outbound email.")
        return False

    role_name = "cat teacher" if role == "cat" else "kitten programmer"
    text = (
        f"Welcome to CatCh, {role_name}.\n\n"
        f"Your verification code is: {verification_code}\n\n"
        "This code expires in 10 minutes."
    )
    html = f"""
<html>
  <body>
    <p>Welcome to CatCh, {role_name}.</p>
    <p>Your verification code is <strong>{verification_code}</strong>.</p>
    <p>This code expires in <strong>10 minutes</strong>.</p>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "CatCh verification code"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except smtplib.SMTPException as exc:
        print(f"SMTP error: {exc}")
        return False


def create_jwt_token(user_id: str, email: str, role: UserRole) -> tuple[str, datetime]:
    """Create a role-aware JWT and return it with its expiration time."""

    now = datetime.utcnow()
    expiry = now + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "token_system_enabled": token_system_enabled(role),
        "permissions": permissions_for_role(role),
        "iat": now.timestamp(),
        "exp": expiry.timestamp(),
        "iss": "auth-service",
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expiry


def verify_jwt_token(token: str) -> Optional[dict]:
    """Decode a JWT and return None when it is expired or invalid."""

    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


app = FastAPI(
    title="Auth Service",
    description="CatCh email verification and role-aware JWT generation",
    version="0.2.0",
)


@app.get("/health", tags=["health"])
def health():
    """Return service health information."""

    return {"status": "ok", "service": "auth-service"}


@app.get("/auth/roles", tags=["auth"])
def roles():
    """Return the available CatCh roles and their permissions."""

    return {
        "roles": {
            "kitten": {
                "description": "Student gameplay user",
                "token_system_enabled": True,
                "permissions": permissions_for_role("kitten"),
            },
            "cat": {
                "description": "Teacher and problem creator",
                "token_system_enabled": False,
                "permissions": permissions_for_role("cat"),
            },
        }
    }


@app.post("/auth/send-verification-email", tags=["auth"])
def send_verification_email_endpoint(request: SendVerificationEmailRequest):
    """Create a short-lived email verification code for the requested role."""

    code = str(secrets.randbelow(1_000_000)).zfill(6)
    expiry = datetime.utcnow() + timedelta(minutes=10)
    verification_codes[str(request.email)] = {
        "code": code,
        "role": request.role,
        "created_at": datetime.utcnow(),
        "expires_at": expiry,
        "attempts": 0,
    }

    email_sent = send_verification_email(str(request.email), code, request.role)
    return {
        "success": True,
        "email_sent": email_sent,
        "message": "Verification code created. Configure SMTP to send real email.",
        "role": request.role,
    }


@app.post("/auth/verify-email", response_model=AuthResponse, tags=["auth"])
def verify_email_endpoint(request: VerifyEmailRequest):
    """Validate a verification code and issue a role-aware JWT."""

    email = str(request.email)
    stored = verification_codes.get(email)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found for this email",
        )

    if datetime.utcnow() > stored["expires_at"]:
        del verification_codes[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired",
        )

    if stored["attempts"] >= 5:
        del verification_codes[email]
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts",
        )

    if stored["code"] != request.code:
        stored["attempts"] += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    role: UserRole = stored.get("role", request.role)
    user_id = f"{role}_{int(datetime.utcnow().timestamp() * 1000)}"
    token, expiry = create_jwt_token(user_id, email, role)
    del verification_codes[email]

    return AuthResponse(
        token=token,
        user_id=user_id,
        email=request.email,
        role=role,
        expires_at=expiry.isoformat(),
        token_system_enabled=token_system_enabled(role),
        permissions=permissions_for_role(role),
    )


@app.post("/auth/verify-token", response_model=TokenValidationResponse, tags=["auth"])
def verify_token_endpoint(request: VerifyTokenRequest):
    """Validate a JWT and return its decoded auth context."""

    payload = verify_jwt_token(request.token)
    if not payload:
        return TokenValidationResponse(valid=False)

    expiry_ts = payload.get("exp")
    expiry_dt = datetime.fromtimestamp(expiry_ts) if expiry_ts else None
    role = payload.get("role", "kitten")

    return TokenValidationResponse(
        valid=True,
        user_id=payload.get("sub"),
        email=payload.get("email"),
        role=role,
        expires_at=expiry_dt.isoformat() if expiry_dt else None,
        token_system_enabled=token_system_enabled(role),
        permissions=permissions_for_role(role),
    )


@app.post("/auth/refresh-token", response_model=AuthResponse, tags=["auth"])
def refresh_token_endpoint(request: TokenRefreshRequest):
    """Refresh a valid JWT while preserving the user's role."""

    payload = verify_jwt_token(request.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    role = payload.get("role", "kitten")
    token, expiry = create_jwt_token(payload["sub"], payload["email"], role)
    return AuthResponse(
        token=token,
        user_id=payload["sub"],
        email=payload["email"],
        role=role,
        expires_at=expiry.isoformat(),
        token_system_enabled=token_system_enabled(role),
        permissions=permissions_for_role(role),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
