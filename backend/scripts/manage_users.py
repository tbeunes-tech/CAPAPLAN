"""Gestion des comptes (§8.1).

    python -m scripts.manage_users create --email a@x.fr --password secret --role admin
    python -m scripts.manage_users seed-demo        # crée admin/contributor/reader de démo
    python -m scripts.manage_users list
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models import User
from app.security import ROLES, hash_password

DEMO = [
    ("admin@demo.fr", "admin123", "admin", "Admin Démo"),
    ("contrib@demo.fr", "contrib123", "contributor", "Contributeur Démo"),
    ("reader@demo.fr", "reader123", "reader", "Lecteur Démo"),
]


def _engine(url: str):
    eng = create_engine(url, future=True)
    Base.metadata.create_all(eng)  # idempotent ; en prod, `alembic upgrade head`
    return eng


def upsert(db: Session, email: str, password: str, role: str, full_name: str | None) -> User:
    if role not in ROLES:
        raise SystemExit(f"rôle invalide: {role} (attendu: {', '.join(sorted(ROLES))})")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
    user.password_hash = hash_password(password)
    user.role = role
    if full_name:
        user.full_name = full_name
    user.is_active = True
    return user


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gestion des comptes (§8.1).")
    p.add_argument("--database-url", default=settings.database_url)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("--email", required=True)
    c.add_argument("--password", required=True)
    c.add_argument("--role", required=True)
    c.add_argument("--name", default=None)

    sub.add_parser("seed-demo")
    sub.add_parser("list")

    args = p.parse_args(argv)
    with Session(_engine(args.database_url), expire_on_commit=False) as db:
        if args.cmd == "create":
            u = upsert(db, args.email, args.password, args.role, args.name)
            db.commit()
            print(f"✓ {u.email} ({u.role})")
        elif args.cmd == "seed-demo":
            for email, pw, role, name in DEMO:
                upsert(db, email, pw, role, name)
            db.commit()
            print("✓ comptes de démo créés :")
            for email, pw, role, _ in DEMO:
                print(f"   {role:12} {email}  /  {pw}")
        elif args.cmd == "list":
            for u in db.scalars(select(User).order_by(User.email)):
                print(f"   {u.role:12} {u.email}  {'(actif)' if u.is_active else '(inactif)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
