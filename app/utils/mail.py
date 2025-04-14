"""
Email utility module for LeagueLedger using FastAPI-Mail
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables if not already loaded
load_dotenv()

# Get mail settings from environment variables or use default values
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@leagueledger.com")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.example.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "LeagueLedger")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
USE_CREDENTIALS = os.getenv("MAIL_USE_CREDENTIALS", "True").lower() == "true"
VALIDATE_CERTS = os.getenv("MAIL_VALIDATE_CERTS", "True").lower() == "true"
APP_BASE_URL = os.getenv("LEAGUELEDGER_BASE_URL", os.getenv("APP_BASE_URL", "http://localhost:8000"))

# Configure Jinja2 for email templates
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(template_dir))

# Configure email connection
conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=USE_CREDENTIALS,
    VALIDATE_CERTS=VALIDATE_CERTS
)

async def send_email(
    email_to: List[EmailStr],
    subject: str,
    html_content: str,
    background_tasks: BackgroundTasks
):
    """Generic function to send emails"""
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email_to] if isinstance(email_to, str) else email_to,
            body=html_content,
            subtype="html"
        )
        
        fm = FastMail(conf)
        
        # Send email in the background to avoid blocking the main thread
        background_tasks.add_task(fm.send_message, message)
        logger.info(f"Email queued for sending to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

async def send_password_reset_email(
    email_to: str,
    username: str,
    reset_token: str,
    background_tasks: BackgroundTasks
):
    """Send password reset email with a reset link"""
    try:
        # Create reset URL with token
        reset_url = f"{APP_BASE_URL}/auth/reset-password?token={reset_token}"
        
        # Get the email template
        template = env.get_template("email/password_reset.html")
        
        # Render the HTML content with variables
        html_content = template.render(
            username=username,
            reset_url=reset_url,
            token=reset_token
        )
        
        # Send email
        subject = "Password Reset Request - LeagueLedger"
        await send_email(
            email_to=email_to,
            subject=subject,
            html_content=html_content,
            background_tasks=background_tasks
        )
        logger.info(f"Password reset email sent to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return False

async def send_team_join_request_notification(
    captain_email: str,
    captain_name: str, 
    requester_name: str,
    team_name: str,
    message: str,
    approval_token: str,
    background_tasks: BackgroundTasks
):
    """Send email notification to team captain about join request"""
    try:
        # Create approval/denial URLs
        approve_url = f"{APP_BASE_URL}/teams/approve-request/{approval_token}"
        deny_url = f"{APP_BASE_URL}/teams/deny-request/{approval_token}"
        
        # Get the email template
        template = env.get_template("email/team_join_request.html")
        
        # Render the HTML content with variables
        html_content = template.render(
            captain_name=captain_name,
            requester_name=requester_name,
            team_name=team_name,
            message=message,
            approve_url=approve_url,
            deny_url=deny_url
        )
        
        # Send email
        subject = f"Team Join Request - {requester_name} wants to join {team_name}"
        await send_email(
            email_to=captain_email,
            subject=subject,
            html_content=html_content,
            background_tasks=background_tasks
        )
        logger.info(f"Team join request notification sent to {captain_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send team join request notification: {str(e)}")
        return False

async def send_verification_email(
    email_to=None,
    username: str = None,
    verification_token: str = None,
    background_tasks: BackgroundTasks = None,
    email=None,  # Added for backward compatibility
):
    """Send email verification link to newly registered users"""
    try:
        # Use email parameter if email_to is not provided
        recipient_email = email_to if email_to is not None else email
        
        if not recipient_email:
            logger.error("No email address provided for verification email")
            return False
            
        # Create verification URL with token
        verification_link = f"{APP_BASE_URL}/auth/verify-email?token={verification_token}"
        
        # Get the email template
        template = env.get_template("email/email_verification.html")
        
        # Render the HTML content with variables
        html_content = template.render(
            username=username,
            verification_link=verification_link
        )
        
        # Send email
        subject = "Verify Your Email Address - LeagueLedger"
        await send_email(
            email_to=recipient_email,
            subject=subject,
            html_content=html_content,
            background_tasks=background_tasks
        )
        logger.info(f"Verification email sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        return False

async def send_join_request_response(
    user_email: str,
    username: str,
    team_name: str,
    is_approved: bool,
    background_tasks: BackgroundTasks
):
    """Send email notification about join request approval/denial"""
    try:
        # Get the email template
        template = env.get_template("email/join_request_response.html")
        
        # Render the HTML content with variables
        html_content = template.render(
            username=username,
            team_name=team_name,
            is_approved=is_approved,
            base_url=APP_BASE_URL
        )
        
        # Send email
        status = "Approved" if is_approved else "Denied"
        subject = f"Team Join Request {status} - {team_name}"
        await send_email(
            email_to=user_email,
            subject=subject,
            html_content=html_content,
            background_tasks=background_tasks
        )
        logger.info(f"Join request response email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send join request response email: {str(e)}")
        return False
