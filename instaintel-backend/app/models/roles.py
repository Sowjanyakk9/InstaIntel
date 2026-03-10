from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Role(Base):

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True)

    users = relationship("UserRole", back_populates="role")


class UserRole(Base):

    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

    user = relationship("User", back_populates="roles")

    role = relationship("Role", back_populates="users")