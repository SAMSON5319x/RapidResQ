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
import firebase_admin
from firebase_admin import auth, credentials, firestore
from kivy.uix.screenmanager import ScreenManager
from student_dashboard import StudentDashboard

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
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:  # ✅ Prevent multiple initializations
    firebase_admin.initialize_app(cred)
db = firestore.client()  # ✅ This is for Firestore!

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

class DashboardScreen(Screen):
    pass

class RegisterScreen(Screen):
    pass

class ForgotPasswordScreen(Screen):
    pass

class ResetPasswordScreen(Screen):
    pass

class HomeScreen(Screen):
    pass
class WindowManager(ScreenManager):
    pass

class MainApp(MDApp):
    def build(self):
        self.current_user_id = None  # ✅ Store logged-in user ID
        sm = WindowManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(StudentDashboard(name="student_dashboard"))  
        sm.add_widget(StaffDashboard(name="staff_dashboard"))  
        sm.add_widget(AdminDashboard(name="admin_dashboard"))  
        return sm


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
        pattern = r"^[a-zA-Z0-9._%+-]+@citchennai\.net$"  # ✅ Accept only 'citchennai.net' domain
        return bool(re.match(pattern, email))

    def validate_password(self, password):
        """Validate password strength"""
        if len(password) < 6:  # Firebase requires minimum 6 characters
            return False, "Password must be at least 6 characters long"
        return True, "Password is valid"

    def login(self, email, password):
        try:
            if not email.strip() or not password.strip():
                raise ValueError("Please fill in all fields")

            if not self.is_valid_email(email):
                raise ValueError(f"Invalid email format: {email}")

            # ✅ Firebase Authentication
            user = auth.get_user_by_email(email)
            user_id = user.uid  

            # ✅ Fetch user role
            doc_ref = db.collection("users").document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                raise ValueError("User data not found in Firestore!")

            user_data = doc.to_dict()
            role = user_data.get("role", "unknown")

            # ✅ Store user ID
            self.current_user_id = user_id  

            # ✅ Ensure screen exists before switching
            if role == "student":
                if not self.root.has_screen("student_dashboard"):
                    self.root.add_widget(StudentDashboard(name="student_dashboard"))
                self.root.get_screen("student_dashboard").load_student_data(user_id)
                self.root.current = "student_dashboard"

            elif role == "staff":
                if not self.root.has_screen("staff_dashboard"):
                    self.root.add_widget(StaffDashboard(name="staff_dashboard"))
                self.root.get_screen("staff_dashboard").load_staff_data(user_id)
                self.root.current = "staff_dashboard"

            elif role == "admin":
                if not self.root.has_screen("admin_dashboard"):
                    self.root.add_widget(AdminDashboard(name="admin_dashboard"))
                self.root.get_screen("admin_dashboard").load_admin_data(user_id)
                self.root.current = "admin_dashboard"

            else:
                raise ValueError("Unauthorized Access!")

            self.show_dialog("Success", f"Login successful! Welcome, {role.capitalize()}")

        except ValueError as ve:
            self.show_dialog("Error", str(ve))

        except Exception as e:
            self.show_dialog("Error", f"Unexpected error: {str(e)}")

# ✅ Make get_role_from_email a static method
@staticmethod
def get_role_from_email(email):
    """Automatically determine user role from email format"""
    if re.match(r".+\.cs\d{4}@citchennai\.net", email):  # Student email format
        return "student"
    elif re.match(r"^[^@]+@citchennai\.net$", email):  # Staff email format
        return "staff"
    else:
        return "unknown"  # Admins are manually assigned


    def register(self, name, reg_no, dept, phone, father_phone, mother_phone, email, password, confirm_password):
        """Handle student registration with additional details"""
        try:
            # 🔹 Ensure all fields are filled
            if not all([name.strip(), reg_no.strip(), dept.strip(), phone.strip(), father_phone.strip(), mother_phone.strip(), email.strip(), password.strip(), confirm_password.strip()]):
                raise ValueError("Please fill in all fields")

            # 🔹 Validate Email Format
            if not self.is_valid_email(email):
                raise ValueError("Invalid email format")

            # 🔹 Check Password Match
            if password != confirm_password:
                raise ValueError("Passwords do not match")

            # 🔹 Validate Password Strength
            is_valid, msg = self.validate_password(password)
            if not is_valid:
                raise ValueError(msg)

            # 🔹 Auto-Detect Role from Email
            role = get_role_from_email(email)  # ✅ Ensure this function exists
            if role == "unknown":
                raise ValueError("Only college email IDs are allowed for registration.")

            # 🔹 Create Firebase Authentication User
            user = auth.create_user(email=email, password=password)
            user_id = user.uid  # ✅ Corrected UID retrieval

            # 🔹 Store Student Data in Firestore
            student_data = {
                "name": name,
                "reg_no": reg_no,
                "dept": dept,
                "phone": phone,
                "father_phone": father_phone,
                "mother_phone": mother_phone,
                "email": email,
                "role": role,
                "created_at": firestore.SERVER_TIMESTAMP  # ✅ Uses Firestore's timestamp
            }
            db.collection("users").document(user_id).set(student_data)

            self.show_dialog("Success", "Account created successfully! Please login.")
            self.root.current = "login"

        except HTTPError as e:
            error_message = "Registration failed"
            if "EMAIL_EXISTS" in str(e):
                error_message = "This email is already registered"
            self.show_dialog("Error", error_message)

        except firebase_admin.exceptions.FirebaseError as e:
            self.show_dialog("Error", f"Firebase Error: {str(e)}")

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
            sender_email = os.getenv("SMTP_EMAIL")
            sender_password = os.getenv("SMTP_PASSWORD")

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

            if not self.current_email:
                raise ValueError("Email not found. Please try again")

            # Get user by email
            users = auth.get_user_by_email(self.current_email)
            if not users:
                raise ValueError("User not found")

            # Update password in Firebase
            user = auth.sign_in_with_email_and_password(self.current_email, new_password)
            auth.update_password(user['idToken'], new_password)

            self.show_dialog("Success", "Password reset successfully!")
            self.current_email = None  # Clear the stored email
            self.root.current = "login"

        except HTTPError as e:
            error_message = "Password reset failed"
            if "INVALID_PASSWORD" in str(e):
                error_message = "Invalid password format"
            self.show_dialog("Error", error_message)

        except Exception as e:
            self.show_dialog("Error", str(e))


if __name__ == "__main__":
    LoginApp().run()
