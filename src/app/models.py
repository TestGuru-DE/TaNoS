from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import Base
from sqlalchemy import Boolean, String


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    categories = relationship("Category", back_populates="project", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="project", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    project = relationship("Project", back_populates="categories")
    values = relationship("Value", back_populates="category", cascade="all, delete-orphan")

class Value(Base):
    __tablename__ = "values"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    value = Column(String(500), nullable=False)
    risk_weight = Column(Integer, default=1, nullable=False)
    allowed = Column(Boolean, nullable=False, default=True)      # NEU
    vtype = Column(String(20), nullable=False, default="string") # NEU
    order_index = Column(Integer, nullable=False, default=0)

    category = relationship("Category", back_populates="values")

class Generation(Base):
    __tablename__ = "generations"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    strategy = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    coverage_meta = Column(Text, nullable=True)  # JSON-String (optional)

    project = relationship("Project", back_populates="generations")
    testcases = relationship("TestCase", back_populates="generation", cascade="all, delete-orphan")

class TestCase(Base):
    __tablename__ = "testcases"
    id = Column(Integer, primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)

    generation = relationship("Generation", back_populates="testcases")
    values = relationship("TestCaseValue", back_populates="testcase", cascade="all, delete-orphan")

class TestCaseValue(Base):
    __tablename__ = "testcase_values"
    id = Column(Integer, primary_key=True)
    testcase_id = Column(Integer, ForeignKey("testcases.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    value = Column(String(500), nullable=False)

    testcase = relationship("TestCase", back_populates="values")

class Rule(Base):
    """
    Abhängigkeitsregel auf Projektebene:
    - type: aktuell nur 'dependency' (Wenn KategorieA=WertX, Dann KategorieB=WertY)
    - if_category_id / if_value: Auslöser (Antezedens)
    - then_category_id / then_value: Konsequenz (Konzedens)

    Alle IDs referenzieren das aktuelle Projekt (project_id).
    """
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(String(20), nullable=False, default="dependency")

    if_category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    if_value       = Column(String, nullable=False)

    then_category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    then_value       = Column(String, nullable=False)
    # Für type='combine': Ziel-Kategorie steht in then_category_id,
    # die Zielwerte stehen JSON-kodiert als Array in then_values_json (z. B. '["DE","US","FR"]').
    then_values_json = Column(Text, nullable=True)

