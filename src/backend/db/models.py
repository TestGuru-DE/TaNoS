from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .connection import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    parent = relationship("Category", remote_side=[id], backref="children")
    values = relationship("Value", back_populates="category")


class Value(Base):
    __tablename__ = "values"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String, nullable=False)
    schaden = Column(Float, default=0.0)
    nutzung = Column(Float, default=0.0)
    gewichtung = Column(Float, default=0.0)
    status = Column(String, default="allowed")

    category = relationship("Category", back_populates="values")


class TestCase(Base):
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    data = Column(JSON, nullable=False)   # z. B. {"Gewicht": "500 g", "Größe": "klein"}

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # z. B. exclude | dependency | risk
    definition = Column(JSON, nullable=False)  # Bedingungen, z. B. {"Gewicht": ["500g"], "Größe": ["Klein"]}

