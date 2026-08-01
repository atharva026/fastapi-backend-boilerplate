from typing import Optional
from functools import lru_cache
import uuid
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.app.core.config import config
from src.app.email.utils import render_email_template
from src.app.core.logging import get_logger

logger = get_logger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = config.EMAIL_CONFIG.email_host
        self.smtp_port = config.EMAIL_CONFIG.email_port
        self.username = config.EMAIL_CONFIG.email_username
        self.password = config.EMAIL_CONFIG.email_password
        self.from_email = config.EMAIL_CONFIG.email_from
        self.use_tls = True

    async def send_email(
        self,
        user_id: uuid.UUID,
        to_email: str,
        email_type: str,
        subject: str,
        html_content: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            user_id: ID of the user
            to_email: Recipient email address
            email_type: Type of email being sent (for logging)
            subject: Email subject line
            html_content: HTML content of the email
            cc: Optional CC email address
            bcc: Optional BCC email address
            reply_to: Optional reply-to email address
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        log_data = {
            "user_id": user_id,
            "email_type": email_type,
            "subject": subject,
            "to_email": to_email
        }

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email

            if cc:
                message["Cc"] = cc
            if bcc:
                message["Bcc"] = bcc
            if reply_to:
                message["Reply-To"] = reply_to

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=self.use_tls,
                username=self.username,
                password=self.password,
            )

            logger.info(f"(email_service - send_email) Email sent successfully : {log_data}")
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(f"(email_service - send_email) SMTP error sending email: {log_data} - Error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"(email_service - send_email) Unexpected error sending email: {log_data} - Error: {str(e)}", exc_info=True)
            return False


    async def send_welcome_email(
        self, 
        user_id: uuid.UUID, 
        to_email: str, 
        name: str
    ):
        """
        Send a welcome email.

        Args:
            user_id: ID of the user
            to_email: Recipient email address
            name: Name of the recipient
            
        Returns:
            bool: True if email sent successfully, False otherwise

        """
        try:
            html_content = render_email_template(
                "emails/welcome_email.html",
                {"name": name}
            )
        except Exception as e:
            logger.error(f"(email_service - send_welcome_email) Failed to render email template: {str(e)}")
            return False

        return await self.send_email(
            user_id=user_id,
            to_email=to_email,
            email_type="WELCOME",
            subject="Welcome to Our Platform!",
            html_content=html_content
        )

    async def send_password_reset_email(
        self, 
        user_id: uuid.UUID, 
        to_email: str, 
        reset_token: str, 
        name: str
    ):
        """
        Send a password reset email.

        Args:
            user_id: ID of the user
            to_email: Recipient email address
            reset_token: Password reset token
            name: Name of the recipient
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        reset_url = f"{config.FRONTEND_URL}/reset-password?token={reset_token}"

        try:
            html_content = render_email_template(
                "emails/password_reset.html",
                {
                    "name": name,
                    "reset_url": reset_url,
                    "expire_minutes": config.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
                }
            )
        except Exception as e:
            logger.error(f"(email_service - send_password_reset_email) Failed to render email template: {str(e)}")
            return False

        return await self.send_email(
            user_id=user_id,
            to_email=to_email,
            email_type="PASSWORD_RESET",
            subject="Password Reset Requested",
            html_content=html_content
        )

    async def send_verification_email(
        self, 
        user_id: uuid.UUID, 
        to_email: str, 
        verification_token: str, 
        name: str
    ):
        """
        Send a password reset email.

        Args:
            user_id: ID of the user
            to_email: Recipient email address
            verification_token: email verification token
            name: Name of the recipient
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        verification_url = f"{config.FRONTEND_URL}/verify-email?token={verification_token}"

        try:
            html_content = render_email_template(
                "emails/email_verification.html",
                {
                    "name": name,
                    "verification_url": verification_url,
                    "expire_hours": config.VERIFICATION_TOKEN_EXPIRE_HOURS
                }
            )
        except Exception as e:
            logger.error(f"(email_service - send_verification_email) Failed to render email template: {str(e)}")
            return False

        return await self.send_email(
            user_id=user_id,
            to_email=to_email,
            email_type="EMAIL_VERIFICATION",
            subject="Verify Your Email Address",
            html_content=html_content
        )
    
@lru_cache()
def get_email_service() -> EmailService:
    return EmailService()