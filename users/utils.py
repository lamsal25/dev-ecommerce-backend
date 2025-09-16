import random
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_otp():
    """Generate a 6-digit OTP code"""
    return str(random.randint(100000, 999999))

def send_otp_email(email, code, user_name=None):
    """
    Send OTP email with robust error handling
    Args:
        email (str): Recipient email
        code (str): OTP code
        user_name (str, optional): Recipient name for personalization
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = "Your Verification Code"
    message = f"Hello {user_name or 'there'},\n\nYour verification code is: {code}"
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,  # Use from settings
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP to {email}: {str(e)}")
        return False