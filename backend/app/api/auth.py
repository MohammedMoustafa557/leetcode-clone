from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select

from app.api.deps import DB, CurrentUser
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut.model_validate(user))


def _authenticate(db, login: str, password: str) -> User:
    login = login.strip().lower()
    user = db.scalar(
        select(User).where(or_(func.lower(User.username) == login, func.lower(User.email) == login))
    )
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username/email or password")
    return user


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DB) -> TokenOut:
    email = body.email.lower()
    exists = db.scalar(
        select(User).where(
            or_(func.lower(User.username) == body.username.lower(), User.email == email)
        )
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already registered")
    user = User(username=body.username, email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB) -> TokenOut:
    return _token(_authenticate(db, body.login, body.password))


@router.post("/token", response_model=TokenOut, include_in_schema=True)
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> TokenOut:
    """OAuth2 password flow (used by the Swagger "Authorize" button)."""
    return _token(_authenticate(db, form.username, form.password))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
