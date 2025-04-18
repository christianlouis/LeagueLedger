"""
Email utility module for LeagueLedger using Python's built-in email and smtplib packages
"""
import os
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import BackgroundTasks
from pydantic import EmailStr
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
import logging
import re
from bs4 import BeautifulSoup

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
APP_BASE_URL = os.getenv("LEAGUELEDGER_BASE_URL", os.getenv("APP_BASE_URL", "http://localhost:8000"))

# Configure Jinja2 for email templates
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(template_dir))

def html_to_plain_text(html_content):
    """
    Convert HTML content to plain text for email alternatives.
    This helps improve email deliverability by providing a plain text version.
    """
    if not html_content:
        return ""
    
    # Use BeautifulSoup to parse HTML
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get text from HTML
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up extra whitespace and handle links
        text = re.sub(r'\n\s+\n', '\n\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    except Exception as e:
        logger.error(f"Error converting HTML to plain text: {str(e)}")
        # Fallback: Basic HTML tag removal
        plain = re.sub('<.*?>', '', html_content)
        return plain.replace('&nbsp;', ' ').strip()

async def _send_email_async(
    email_to: Union[str, List[str]],
    subject: str,
    html_content: str,
    plain_text_content: Optional[str] = None
) -> bool:
    """
    Asynchronous function to send emails using Python's built-in email and smtplib packages.
    This function handles the actual sending of the email.
    """
    # Convert single email to list if needed
    recipients = [email_to] if isinstance(email_to, str) else email_to
    
    # Generate plain text from HTML if not provided
    if plain_text_content is None:
        plain_text_content = html_to_plain_text(html_content)
    
    try:
        # Create multipart message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        msg['To'] = ", ".join(recipients)
        msg['Date'] = formatdate(localtime=True)
        
        # Attach plain text part first (will be displayed if HTML not supported)
        # RFC 2046 defines that the last part is preferred
        part1 = MIMEText(plain_text_content, 'plain', 'utf-8')
        msg.attach(part1)
        
        # Attach HTML part last (will be preferred by most email clients)
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        # Run SMTP connection in a separate thread to avoid blocking
        result = await asyncio.to_thread(_send_smtp_email, msg, recipients)
        return result
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def _send_smtp_email(msg, recipients):
    """
    Helper function to handle SMTP connection and sending.
    This runs in a separate thread to avoid blocking the main event loop.
    """
    try:
        # Choose the appropriate SMTP connection method
        if MAIL_SSL_TLS:
            server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT)
        else:
            server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
            
            # Use STARTTLS if configured
            if MAIL_STARTTLS:
                server.starttls()
        
        # Login if credentials provided
        if MAIL_USERNAME and MAIL_PASSWORD:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {recipients}")
        return True
    except Exception as e:
        logger.error(f"SMTP error: {str(e)}")
        return False

async def send_email(
    email_to: Union[str, List[str]],
    subject: str,
    html_content: str,
    background_tasks: BackgroundTasks,
    plain_text_content: Optional[str] = None
) -> bool:
    """Generic function to send emails"""
    try:
        # Add email sending to background tasks
        background_tasks.add_task(
            _send_email_async,
            email_to=email_to,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text_content
        )
        logger.info(f"Email queued for sending to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue email: {str(e)}")
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
        
        # Generate plain text version explicitly
        plain_text = f"""
Hello {username},

Thank you for creating an account with LeagueLedger, your pub quiz team tracking platform. We're excited to have you join our community!

To ensure account security and complete your registration, please verify your email address by visiting this link:
{verification_link}

This verification step helps us keep your account secure and allows you to:
- Create or join teams
- Track your quiz night scores
- Earn points and achievements
- Climb the leaderboards

If you did not create an account with LeagueLedger, please disregard this email.

Best regards,
The LeagueLedger Team

© 2025 LeagueLedger. All rights reserved.
This email was sent to verify your account registration.
"""
        
        # Send email with both HTML and plain text versions
        subject = "Verify Your Email Address - LeagueLedger"
        await send_email(
            email_to=recipient_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text,
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

async def send_welcome_email(
    email_to: str,
    username: str,
    background_tasks: BackgroundTasks
):
    """Send welcome email to newly registered users after verification"""
    try:
        # Get the email template
        template = env.get_template("email/welcome.html")
        
        # Render the HTML content with variables
        html_content = template.render(
            username=username,
            base_url=APP_BASE_URL
        )
        
        # Generate plain text version
        plain_text_content = html_to_plain_text(html_content)
        
        # Send email
        subject = "Welcome to LeagueLedger!"
        await send_email(
            email_to=email_to,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text_content,
            background_tasks=background_tasks
        )
        logger.info(f"Welcome email sent to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False
