#!/usr/bin/env python3
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    memberships = relationship("TeamMembership", back_populates="user")
    teams = relationship("TeamMember", back_populates="user")
    points = relationship("UserPoints", back_populates="user")
    events_attended = relationship("EventAttendee", back_populates="user")


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
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)  # For team privacy setting
    created_at = Column(DateTime, server_default=func.now())  # For team founded date
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    memberships = relationship("TeamMembership", back_populates="team")
    members = relationship("TeamMember", back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_membership"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="memberships")
    team = relationship("Team", back_populates="memberships")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    is_captain = Column(Boolean, default=False)
    joined_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="members")


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


class TeamAchievement(Base):
    __tablename__ = "team_achievements"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    name = Column(String(255), nullable=False)  # e.g., "1st Place"
    event_name = Column(String(255), nullable=True)  # e.g., "History Night"
    description = Column(Text, nullable=True)
    achieved_at = Column(DateTime, server_default=func.now())
    
    team = relationship("Team")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    event_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    attendees = relationship("EventAttendee", back_populates="event")


class EventAttendee(Base):
    __tablename__ = "event_attendees"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in_time = Column(DateTime, server_default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="attendees")
    user = relationship("User", back_populates="events_attended")


class UserPoints(Base):
    __tablename__ = "user_points"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points = Column(Float, nullable=False, default=0)
    reason = Column(String(200), nullable=True)
    awarded_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="points")


class QRCode(Base):
    __tablename__ = "qr_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)
    points = Column(Float, default=1.0, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    max_uses = Column(Integer, nullable=True)  # null = unlimited
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)  # null = never expires
    
    # Relationships
    redemptions = relationship("QRCodeRedemption", back_populates="qr_code")


class QRCodeRedemption(Base):
    __tablename__ = "qr_code_redemptions"
    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    qr_code = relationship("QRCode", back_populates="redemptions")
    user = relationship("User")
