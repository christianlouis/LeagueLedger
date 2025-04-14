#!/usr/bin/env python3
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# This Base should be the single source of truth
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Can be null for OAuth users
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires_at = Column(DateTime, nullable=True)  # Added field for verification token expiration
    last_verification_email_sent = Column(DateTime, nullable=True)  # Track when verification email was last sent
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # OAuth fields
    is_oauth_user = Column(Boolean, default=False)
    oauth_id = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    picture = Column(String(255), nullable=True)  # URL to profile picture

    # Relationships
    memberships = relationship("TeamMembership", back_populates="user")
    points = relationship("UserPoints", back_populates="user")
    events_attended = relationship("EventAttendee", back_populates="user")
    owned_teams = relationship("Team", back_populates="owner")

    def __repr__(self):
        return f"<User {self.username}>"


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
    logo_url = Column(String(255), nullable=True)  # Add logo URL field
    is_public = Column(Boolean, default=False)  # For team privacy setting
    is_open = Column(Boolean, default=False)  # Whether anyone can join without approval
    is_active = Column(Boolean, default=True)  # Add this column to fix the error
    created_at = Column(DateTime, default=datetime.utcnow)  # For team founded date
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    members = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="owned_teams")


class TeamJoinRequest(Base):
    __tablename__ = "team_join_requests"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String(500), nullable=True)  # Specified length for VARCHAR
    status = Column(String(20), default="pending")  # pending, approved, denied
    request_token = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team")
    user = relationship("User")

    __table_args__ = (UniqueConstraint('team_id', 'user_id', 'status', name='_team_user_request_status_uc'),)


class TeamMembership(Base):
    __tablename__ = "team_membership"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)  # Added captain status
    joined_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="memberships")
    team = relationship("Team", back_populates="members")

    __table_args__ = (UniqueConstraint('user_id', 'team_id', name='_user_team_uc'),)


class QRSet(Base):
    """A set of related QR codes, such as codes for different placements in a quiz"""
    __tablename__ = "qr_sets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    qr_codes = relationship("QRCode", back_populates="qr_set")
    creator = relationship("User")


class QRCode(Base):
    """Unified QR code model that includes all the functionality of the old QRTicket and QRCode models"""
    __tablename__ = "qr_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, index=True, nullable=False)  # Unique token
    points = Column(Float, default=0, nullable=False)
    title = Column(String(100), nullable=True)  # e.g., "1st Place", "2nd Place"
    description = Column(String(255), nullable=True)
    
    # Set relationship
    qr_set_id = Column(Integer, ForeignKey("qr_sets.id"), nullable=True)
    qr_set = relationship("QRSet", back_populates="qr_codes")
    
    # Achievement relationship
    achievement_name = Column(String(255), nullable=True)  # Name of achievement this QR code grants
    is_achievement_only = Column(Boolean, default=False)  # True for QR codes that grant achievements but no points
    
    # Redemption info
    redeemed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    redeemed_at_team = Column(Integer, ForeignKey("teams.id"), nullable=True)
    redeemed_at = Column(DateTime, nullable=True)
    used = Column(Boolean, default=False)
    
    # Extended functionality
    max_uses = Column(Integer, nullable=True)  # null = single use, >1 for multi-use codes
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)  # null = never expires
    
    # Event tracking
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    event = relationship("Event")

    def __repr__(self):
        if self.title:
            return f"QR Code: {self.title} ({self.points} points)"
        return f"QR Code: {self.points} points"


class TeamAchievement(Base):
    __tablename__ = "team_achievements"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    name = Column(String(255), nullable=False)  # e.g., "1st Place"
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    description = Column(Text, nullable=True)
    achieved_at = Column(DateTime, server_default=func.now())
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"), nullable=True)
    
    # Relationships
    team = relationship("Team")
    event = relationship("Event")
    qr_code = relationship("QRCode")


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
