from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone
import jwt  # PyJWT
from jwt import InvalidTokenError

ALGORITHM = "HS256"

def generate_jwt(
    secret: str,
    contents: Dict[str, Any],
    expires_in: Optional[timedelta] = timedelta(hours=1),
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> str:
    """
    Create a compact JWT string signed with HS256.
    - contents: your custom claims (e.g., {"user_id": "...", "role": "..."})
    - expires_in: optional lifetime (default 1h). Pass None for no exp (not recommended).
    - issuer / audience: optional standard claims for extra validation hardening.
    """
    now = datetime.now(timezone.utc)
    payload = {
        **contents,
        "iat": int(now.timestamp()),
    }
    if expires_in is not None:
        payload["exp"] = int((now + expires_in).timestamp())
    if issuer is not None:
        payload["iss"] = issuer
    if audience is not None:
        payload["aud"] = audience

    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    # PyJWT returns str on v2+ for HS256
    return token


def validate_jwt(
    secret: str,
    token: str,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
    leeway: int = 0,
) -> bool:
    """
    Returns True if the token is valid (signature OK and standard claims check out),
    otherwise False. Does NOT return the payload—use extract_jwt_contents for that.
    """
    try:
        jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],  # prevent "alg=none" attacks
            options={"require": [], "verify_signature": True, "verify_exp": True},
            issuer=issuer,
            audience=audience,
            leeway=leeway,  # seconds of tolerance on exp/nbf
        )
        return True
    except InvalidTokenError:
        return False


def extract_jwt_contents(
    secret: str,
    token: str,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
    leeway: int = 0,
) -> Dict[str, Any]:
    """
    Verifies and returns the payload (your claims + std. claims).
    Raises jwt.InvalidTokenError (or subclass) on failure.
    """
    payload = jwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        options={"require": [], "verify_signature": True, "verify_exp": True},
        issuer=issuer,
        audience=audience,
        leeway=leeway,
    )
    return payload