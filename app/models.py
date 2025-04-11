#!/usr/bin/env python3
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Relationship to teams
    memberships = relationship("TeamMembership", back_populates="user")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String(50))  # e.g., "google", "facebook"
    provider_user_id = Column(String(255))
    access_token = Column(String(255))
    expires_at = Column(DateTime, nullable=True)
    refresh_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    
    # Add fields for team detail view
    is_public = Column(Boolean, default=False)  # For team privacy setting
    created_at = Column(DateTime, server_default=func.now())  # For team founded date
    description = Column(Text, nullable=True)  # Optional team description

    # Relationship to memberships
    memberships = relationship("TeamMembership", back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_membership"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    is_admin = Column(Boolean, default=False)
    
    # Add joined_at to track when members joined
    joined_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="memberships")
    team = relationship("Team", back_populates="memberships")


class QRTicket(Base):
    __tablename__ = "qr_tickets"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, index=True)  # Unique token
    points = Column(Integer, default=0)
    redeemed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    redeemed_at_team = Column(Integer, ForeignKey("teams.id"), nullable=True)
    used = Column(Boolean, default=False)
    
    # Add timestamps to track when tickets were created and redeemed
    created_at = Column(DateTime, server_default=func.now())
    redeemed_at = Column(DateTime, nullable=True)
    
    # Add event name to track which quiz event this ticket belongs to
    event_name = Column(String(255), nullable=True)


# New model for team achievements
class TeamAchievement(Base):
    __tablename__ = "team_achievements"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    name = Column(String(255), nullable=False)  # e.g., "1st Place"
    event_name = Column(String(255), nullable=True)  # e.g., "History Night"
    description = Column(Text, nullable=True)
    achieved_at = Column(DateTime, server_default=func.now())
    
    team = relationship("Team")
