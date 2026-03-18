from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, Double
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True)
    name = Column(String)
    owner_email = Column(String)
    created_at = Column(Float)

class User(Base):
    __tablename__ = "users"
    email = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"))
    role = Column(String)
    joined_at = Column(Float)

class RiskAudit(Base):
    __tablename__ = "risk_audit"
    risk_id = Column(String, primary_key=True)
    uid = Column(String)
    email = Column(String)
    team_id = Column(String)
    risk_score = Column(Float)
    decision = Column(String)
    shadow_mode = Column(Integer)
    reasons = Column(String)
    metrics = Column(Text)
    timestamp = Column(Float)
    outcome = Column(String, default="PENDING")

class RiskProfileAudit(Base):
    __tablename__ = "risk_profile_audit"
    audit_id = Column(String, primary_key=True)
    email = Column(String)
    team_id = Column(String)
    actor = Column(String)
    action = Column(String)
    previous_config = Column(Text)
    new_config = Column(Text)
    timestamp = Column(Float)

class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"))
    email = Column(String)
    role = Column(String)
    inviter = Column(String)
    created_at = Column(Float)
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, EXPIRED
