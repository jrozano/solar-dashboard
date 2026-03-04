"""User repository - in-memory store for domain User entities."""

from __future__ import annotations

from threading import Lock

from domain.models import User


class UserRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._users: dict[str, User] = {}

    def create(self, id_: str, name: str, email: str, picture: str) -> User:
        with self._lock:
            u = User(id=id_, name=name, email=email, picture=picture)
            self._users[id_] = u
            return u

    def get(self, id_: str) -> User | None:
        with self._lock:
            return self._users.get(id_)

    def list(self) -> list[User]:
        with self._lock:
            return list(self._users.values())

    def delete(self, id_: str) -> bool:
        with self._lock:
            if id_ in self._users:
                del self._users[id_]
                return True
            return False

    def get_or_create_from_userinfo(self, userinfo: dict) -> User:
        uid = userinfo['sub']
        u = self.get(uid)
        if u:
            return u
        return self.create(
            id_=uid,
            name=userinfo.get('name', ''),
            email=userinfo.get('email', ''),
            picture=userinfo.get('picture', ''),
        )
