from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
import pyrebase
import re
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests.exceptions import HTTPError
from dotenv import load_dotenv
import secrets
import time

# Load environment variables
load_dotenv()

# Firebase Configuration
firebase_config = {
    "apiKey": "AIzaSyCuBHC1DhQwqvJ51EfEvq6Caoph2wAb-Eg",
    "authDomain": "sdghackathon-e00e8.firebaseapp.com",
    "databaseURL": "https://sdghackathon-e00e8-default-rtdb.firebaseio.com",
    "projectId": "sdghackathon-e00e8",
    "storageBucket": "sdghackathon-e00e8.firebasestorage.app",
    "messagingSenderId": "110033294925",
    "appId": "1:110033294925:web:6a297e978e64e1ef7c2e04",
    "measurementId": "G-VEWX5XW0QM"
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

class OTPManager:
    def __init__(self):
        self.otps = {}
        self.max_attempts = 3
        self.otp_expiry = 300  # 5 minutes

    def generate_otp(self, email):
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        timestamp = time.time()
        self.otps[email] = {
            'otp': otp,
            'timestamp': timestamp,
            'attempts': 0
        }
        return otp

    def verify_otp(self, email, otp):
        if email not in self.otps:
            return False, "OTP not found or expired"

        otp_data = self.otps[email]
        if time.time() - otp_data['timestamp'] > self.otp_expiry:
            del self.otps[email]
            return False, "OTP expired"

        if otp_data['attempts'] >= self.max_attempts:
            del self.otps[email]
            return False, "Too many attempts. Please request a new OTP"

        otp_data['attempts'] += 1
        if otp_data['otp'] != otp:
            return False, "Invalid OTP"

        del self.otps[email]
        return True, "OTP verified successfully"

class LoginScreen(Screen):
    pass

class RegisterScreen(Screen):
    pass

class ForgotPasswordScreen(Screen):
    pass

class ResetPasswordScreen(Screen):
    pass

class HomeScreen(Screen):
    pass

class LoginApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.otp_manager = OTPManager()
        self.current_email = None  # To store email during password reset

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        return Builder.load_file("login.kv")

    def show_dialog(self, title, text):
        """Show a popup message using MDDialog"""
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda _: self.dialog.dismiss())]
        )
        self.dialog.open()

    def is_valid_email(self, email):
        """Validate email format using regex"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def validate_password(self, password):
        """Validate password strength"""
        if len(password) < 6:  # Firebase requires minimum 6 characters
            return False, "Password must be at least 6 characters long"
        return True, "Password is valid"

    def login(self, email, password):
        """Handle user login"""
        try:
            if not email.strip() or not password.strip():
                raise ValueError("Please fill in all fields")

            if not self.is_valid_email(email):
                raise ValueError("Invalid email format")

            user = auth.sign_in_with_email_and_password(email, password)
            self.root.current = "home"
            self.show_dialog("Success", "Login successful!")

        except HTTPError as e:
            error_message = "Login failed. Please check your credentials."
            if "INVALID_PASSWORD" in str(e):
                error_message = "Incorrect password"
            elif "EMAIL_NOT_FOUND" in str(e):
                error_message = "Email not found"
            self.show_dialog("Error", error_message)
        except Exception as e:
            self.show_dialog("Error", str(e))

    def register(self, name, email, password, confirm_password):
        """Handle user registration"""
        try:
            if not all([name.strip(), email.strip(), password.strip(), confirm_password.strip()]):
                raise ValueError("Please fill in all fields")

            if not self.is_valid_email(email):
                raise ValueError("Invalid email format")

            if password != confirm_password:
                raise ValueError("Passwords do not match")

            is_valid, msg = self.validate_password(password)
            if not is_valid:
                raise ValueError(msg)

            user = auth.create_user_with_email_and_password(email, password)
            user_id = user['localId']
            
            # Store user data in database
            user_data = {
                "name": name,
                "email": email,
                "created_at": {".sv": "timestamp"}
            }
            db.child("users").child(user_id).set(user_data)
            
            self.show_dialog("Success", "Account created successfully! Please login.")
            self.root.current = "login"

        except HTTPError as e:
            error_message = "Registration failed"
            if "EMAIL_EXISTS" in str(e):
                error_message = "This email is already registered"
            self.show_dialog("Error", error_message)
        except Exception as e:
            self.show_dialog("Error", str(e))

    def send_reset_email(self, email):
        """Send password reset OTP"""
        try:
            if not email.strip():
                raise ValueError("Please enter your email")

            if not self.is_valid_email(email):
                raise ValueError("Invalid email format")

            # Store email for password reset
            self.current_email = email
            
            # Generate OTP
            otp = self.otp_manager.generate_otp(email)

            # Email configuration
            sender_email = "saimukeshr.cs2023@citchennai.net"
            sender_password = "saimukes"

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "Password Reset OTP"

            body = f"""
            Your OTP for password reset is: {otp}
            
            This OTP will expire in 5 minutes.
            If you didn't request this reset, please ignore this email.
            """
            msg.attach(MIMEText(body, 'plain'))

            # Send Email
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            self.show_dialog("Success", "OTP sent! Please check your email.")

        except Exception as e:
            self.show_dialog("Error", f"Failed to send OTP: {str(e)}")

    def verify_otp(self, email, otp):
        """Verify the OTP entered by user"""
        if not otp.strip():
            self.show_dialog("Error", "Please enter OTP")
            return

        success, message = self.otp_manager.verify_otp(email, otp)
        if success:
            self.root.current = "reset_password"
        else:
            self.show_dialog("Error", message)

    def reset_password(self, new_password, confirm_password):
        """Reset user password"""
        try:
            if not new_password.strip() or not confirm_password.strip():
                raise ValueError("Please fill in all fields")

            if new_password != confirm_password:
                raise ValueError("Passwords do not match")

            is_valid, msg = self.validate_password(new_password)
            if not is_valid:
                raise ValueError(msg)

            if self.current_email:
                auth.send_password_reset_email(self.current_email)
                self.show_dialog("Success", "Password reset link sent to your email")
                self.current_email = None
                self.root.current = "login"
            else:
                raise ValueError("Email not found. Please try again")

        except Exception as e:
            self.show_dialog("Error", str(e))

if __name__ == "__main__":
    LoginApp().run()