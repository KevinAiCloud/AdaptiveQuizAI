"""Utility services: PDF extraction, image OCR, text processing, OTP email."""
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def extract_text_from_pdf(file_obj, upload_folder="/tmp/uploads"):
    """Extract text from an uploaded PDF file."""
    try:
        import pypdf
        os.makedirs(upload_folder, exist_ok=True)
        path = os.path.join(upload_folder, file_obj.filename)
        file_obj.save(path)

        reader = pypdf.PdfReader(path)
        text = " ".join(
            [page.extract_text() for page in reader.pages if page.extract_text()]
        )
        try:
            os.remove(path)
        except OSError:
            pass
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def extract_text_from_image(file_obj):
    """Extract text from an image — lightweight fallback without Pillow."""
    try:
        # Try PIL if available locally (not bundled for Vercel)
        from PIL import Image
        img = Image.open(file_obj)
        try:
            import pytesseract
            text = pytesseract.image_to_string(img)
            return text.strip() if text else ""
        except ImportError:
            return "[Image uploaded — OCR requires pytesseract]"
    except ImportError:
        return "[Image OCR not available — please use PDF or text input instead]"
    except Exception as e:
        print(f"Image extraction error: {e}")
        return ""


def clean_text(text):
    """Clean and normalize extracted text."""
    if not text:
        return ""
    import re
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()


# ── OTP Email ────────────────────────────────────────────────────

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def send_otp_email(to_email, otp):
    """Send OTP to user's email via Gmail SMTP using Python's smtplib."""
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_email or not smtp_password:
        print("[OTP] SMTP_EMAIL or SMTP_PASSWORD not set — cannot send OTP")
        return False

    subject = "AdaptiveQuiz — Your Verification Code"
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:30px;
                background:#0a0a1a;color:#fff;border-radius:16px;border:1px solid rgba(255,255,255,0.1);">
        <h2 style="color:#a29bfe;margin-bottom:10px;">🧠 AdaptiveQuiz</h2>
        <p style="color:#ccc;">Your verification code is:</p>
        <div style="font-size:36px;font-weight:800;letter-spacing:8px;color:#6c5ce7;
                    text-align:center;padding:20px;margin:20px 0;background:rgba(108,92,231,0.1);
                    border-radius:12px;border:1px solid rgba(108,92,231,0.3);">
            {otp}
        </div>
        <p style="color:#999;font-size:14px;">This code expires in 10 minutes. Do not share it with anyone.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg.attach(MIMEText(f"Your AdaptiveQuiz verification code is: {otp}", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
        print(f"[OTP] Sent to {to_email}")
        return True
    except Exception as e:
        print(f"[OTP] Email send error: {e}")
        return False
