import secrets
from core.settings import RUNTIME
from apps.api.auth.users import register, identity
from core import db


def main():
    email = "reviewer@gigbid.local"
    if not db.get("authentication", "user", identity(email)):
        password = secrets.token_urlsafe(15)
        register(email, password)
        (RUNTIME / "reviewer-login.txt").write_text(
            f"Local URL: http://127.0.0.1:8000\nEmail: {email}\nPassword: {password}\n\nPrivate local credentials. Do not commit or publish this file.\n"
        )
    print("Reviewer account ready. Private credentials: " + str(RUNTIME / "reviewer-login.txt"))


if __name__ == "__main__":
    main()
