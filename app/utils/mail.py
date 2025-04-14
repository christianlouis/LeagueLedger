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

# Load environment variables if not already loaded
load_dotenv()

# Configure email connection
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "LeagueLedger"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() in ("true", "1", "t"),
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() in ("true", "1", "t"),
    USE_CREDENTIALS=os.getenv("MAIL_USE_CREDENTIALS", "True").lower() in ("true", "1", "t"),
    VALIDATE_CERTS=os.getenv("MAIL_VALIDATE_CERTS", "True").lower() in ("true", "1", "t"),
    TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates' / 'email',
)

# Create FastMail instance
mail = FastMail(mail_config)


async def send_email(
    recipients: List[EmailStr],
    subject: str,
    body: str,
    template_name: Optional[str] = None,
    template_body: Optional[Dict[str, Any]] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    subtype: MessageType = MessageType.html,
    cc: Optional[List[EmailStr]] = None,
    bcc: Optional[List[EmailStr]] = None,
    attachments: Optional[List] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """
    Send an email using FastAPI-Mail
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        body: Email body content (used if template_name is None)
        template_name: Optional name of the template file in the TEMPLATE_FOLDER
        template_body: Optional dictionary of template variables
        background_tasks: Optional BackgroundTasks for sending email in background
        subtype: Message type (html or plain)
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        attachments: Optional list of attachments
        headers: Optional custom email headers
    """
    # Create message schema with empty lists for optional parameters to prevent validation errors
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body if not template_name else None,
        template_body=template_body,
        subtype=subtype,
        cc=cc or [],  # Use empty list if None
        bcc=bcc or [],  # Use empty list if None
        attachments=attachments or [],  # Use empty list if None
        headers=headers,
    )
    
    # Send email
    try:
        if background_tasks:
            if template_name:
                background_tasks.add_task(mail.send_message, message, template_name=template_name)
            else:
                background_tasks.add_task(mail.send_message, message)
        else:
            if template_name:
                await mail.send_message(message, template_name=template_name)
            else:
                await mail.send_message(message)
    except Exception as e:
        # Log the error but don't crash the application
        print(f"Error sending email: {str(e)}")
        # In a production app, you would use a proper logging system


async def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_token: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    Send password reset email
    
    Args:
        email: Recipient email address
        username: User's username
        reset_token: Password reset token
        background_tasks: Optional BackgroundTasks for sending in background
    """
    # Base URL for the application (should be configured in environment vars)
    base_url = os.getenv("LEAGUELEDGER_BASE_URL", "http://localhost:8000")
    reset_link = f"{base_url}/auth/reset-password?token={reset_token}"
    
    # Template data
    template_data = {
        "username": username,
        "reset_link": reset_link,
        "support_email": os.getenv("MAIL_FROM", "support@leagueledger.net"),
        "base_url": base_url,
    }
    
    # Send email
    await send_email(
        recipients=[email],
        subject="Password Reset - LeagueLedger",
        body="",  # Empty as we're using a template
        template_name="password_reset.html",
        template_body=template_data,
        background_tasks=background_tasks,
    )


async def send_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    Send email verification link
    
    Args:
        email: Recipient email address
        username: User's username
        verification_token: Email verification token
        background_tasks: Optional BackgroundTasks for sending in background
    """
    # Base URL for the application
    base_url = os.getenv("LEAGUELEDGER_BASE_URL", "http://localhost:8000")
    verification_link = f"{base_url}/auth/verify-email?token={verification_token}"
    
    # Template data
    template_data = {
        "username": username,
        "verification_link": verification_link,
        "base_url": base_url,
    }
    
    # Send email
    await send_email(
        recipients=[email],
        subject="Verify Your Email - LeagueLedger",
        body="",  # Empty as we're using a template
        template_name="email_verification.html",
        template_body=template_data,
        background_tasks=background_tasks,
    )


async def send_welcome_email(
    email: EmailStr,
    username: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    Send welcome email to new users
    
    Args:
        email: Recipient email address
        username: User's username
        background_tasks: Optional BackgroundTasks for sending in background
    """
    # Get base URL from environment variables
    base_url = os.getenv("LEAGUELEDGER_BASE_URL", "http://localhost:8000")
    
    # Template data
    template_data = {
        "username": username,
        "base_url": base_url,
    }
    
    # Send email
    await send_email(
        recipients=[email],
        subject="Welcome to LeagueLedger!",
        body="",  # Empty as we're using a template
        template_name="welcome.html",
        template_body=template_data,
        background_tasks=background_tasks,
    )
