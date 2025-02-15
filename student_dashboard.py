from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
import firebase_admin
from firebase_admin import credentials, firestore
from kivy.properties import StringProperty
from kivy.clock import Clock

# ✅ Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # 🔹 Firebase credentials
    firebase_admin.initialize_app(cred)

# ✅ Initialize Firestore
db = firestore.client()

class StudentDashboard(Screen):
    student_name = StringProperty("Loading...")
    reg_no = StringProperty("Loading...")
    dept = StringProperty("Loading...")
    phone = StringProperty("Loading...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Builder.load_file("student_dashboard.kv")  # ✅ Load KV file

    def load_student_data(self, user_id):
        """Fetch student data from Firestore and update UI"""
        try:
            print(f"DEBUG: Fetching Firestore data for user_id: {user_id}")  # ✅ Debugging

            doc = db.collection("users").document(user_id).get()

            if doc.exists:
                user_data = doc.to_dict()
                print(f"DEBUG: User Data → {user_data}")  # ✅ Debugging
                
                # ✅ Ensure UI updates properly using Clock
                Clock.schedule_once(lambda dt: self.update_ui(user_data))

            else:
                print("DEBUG: No document found in Firestore")
                Clock.schedule_once(lambda dt: self.show_error("User data not found!"))

        except Exception as e:
            print(f"DEBUG: Error fetching data → {e}")
            Clock.schedule_once(lambda dt: self.show_error(str(e)))

    def update_ui(self, user_data):
        """Update UI labels on the main thread"""
        Clock.schedule_once(lambda dt: self._update_labels(user_data))

    def _update_labels(self, user_data):
        """Update UI labels, clear old text, apply colors, and align text"""
        if hasattr(self, 'ids'):  # ✅ Ensure 'ids' exists before updating
            # ✅ Clear previous text to prevent overlap
            for label in [self.ids.welcome_label, self.ids.student_name, self.ids.reg_no, self.ids.dept, self.ids.phone]:
                label.text = ""  # ✅ Clear old text
                label.color = (0, 0, 0, 1)  # ✅ Set font color to Black
                label.font_size = 24  # ✅ Increase Font Size
                label.halign = "left"  # ✅ Align Text to the Left
                label.size_hint_x = 0.8  # ✅ Adjust width to align better

            # ✅ Set actual user data
            self.ids.welcome_label.text = f"Welcome, {user_data.get('name', 'N/A')}!"
            self.ids.student_name.text = f"Name: {user_data.get('name', 'N/A')}"
            self.ids.reg_no.text = f"Reg No: {user_data.get('reg_no', 'N/A')}"
            self.ids.dept.text = f"Department: {user_data.get('dept', 'N/A')}"
            self.ids.phone.text = f"Phone: {user_data.get('phone', 'N/A')}"
        else:
            print("DEBUG: ERROR - 'ids' not found!")

    def show_error(self, message):
        """Display an error message on the UI"""
        if hasattr(self, 'ids'):
            self.ids.welcome_label.text = f"Error: {message}"
