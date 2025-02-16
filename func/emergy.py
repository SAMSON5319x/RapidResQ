from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty
from plyer import gps
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import json

class EmergencySOSScreen(Screen):
    location_status = StringProperty("Getting location...")
    is_sos_active = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = firestore.client()
        self.dialog = None
        self.current_emergency = None
        self.user_data = None
        
        # Start GPS
        try:
            gps.configure(on_location=self.on_location)
            gps.start(minTime=1000, minDistance=1)
        except NotImplementedError:
            self.location_status = "GPS not available"
            
    def on_location(self, **kwargs):
        self.location = kwargs
        self.location_status = f"Location: {kwargs.get('lat', 0):.4f}, {kwargs.get('lon', 0):.4f}"
        
        # Update emergency location if active
        if self.current_emergency:
            self.update_emergency_location(kwargs.get('lat', 0), kwargs.get('lon', 0))
            
    def load_user_data(self, user_id):
        """Load user's medical and emergency contact data"""
        try:
            doc_ref = self.db.collection("users").document(user_id)
            self.user_data = doc_ref.get().to_dict()
            
            # Update UI with medical data
            self.update_medical_display()
        except Exception as e:
            self.show_dialog("Error", f"Failed to load user data: {str(e)}")
            
    def trigger_sos(self):
        """Handle SOS button press"""
        if not self.is_sos_active:
            try:
                # Create emergency document in Firestore
                emergency_data = {
                    'user_id': self.user_data['id'],
                    'name': self.user_data['name'],
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'status': 'active',
                    'location': {
                        'latitude': self.location.get('lat', 0),
                        'longitude': self.location.get('lon', 0)
                    },
                    'medical_data': {
                        'blood_group': self.user_data.get('blood_group', 'Not specified'),
                        'allergies': self.user_data.get('allergies', []),
                        'medications': self.user_data.get('medications', [])
                    },
                    'emergency_contacts': self.user_data.get('emergency_contacts', [])
                }
                
                # Add to Firestore
                emergency_ref = self.db.collection('emergencies').document()
                emergency_ref.set(emergency_data)
                
                self.current_emergency = emergency_ref.id
                self.is_sos_active = True
                
                # Notify emergency contacts
                self.notify_emergency_contacts()
                
                self.show_dialog("Emergency Alert", 
                               "Emergency services have been notified. Stay calm and wait for assistance.")
                
            except Exception as e:
                self.show_dialog("Error", f"Failed to trigger emergency: {str(e)}")
                
    def cancel_sos(self):
        """Cancel active SOS"""
        if self.current_emergency:
            try:
                emergency_ref = self.db.collection('emergencies').document(self.current_emergency)
                emergency_ref.update({
                    'status': 'cancelled',
                    'cancelled_at': firestore.SERVER_TIMESTAMP
                })
                
                self.current_emergency = None
                self.is_sos_active = False
                
                self.show_dialog("SOS Cancelled", "Emergency alert has been cancelled.")
                
            except Exception as e:
                self.show_dialog("Error", f"Failed to cancel emergency: {str(e)}")
                
    def update_emergency_location(self, lat, lon):
        """Update location for active emergency"""
        if self.current_emergency:
            try:
                emergency_ref = self.db.collection('emergencies').document(self.current_emergency)
                emergency_ref.update({
                    'location': {
                        'latitude': lat,
                        'longitude': lon
                    },
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Failed to update emergency location: {str(e)}")
                
    def notify_emergency_contacts(self):
        """Notify emergency contacts through Firebase Cloud Functions"""
        if self.user_data and 'emergency_contacts' in self.user_data:
            try:
                # This would typically trigger a Cloud Function to handle SMS/email
                notification_data = {
                    'emergency_id': self.current_emergency,
                    'user_name': self.user_data['name'],
                    'contacts': self.user_data['emergency_contacts'],
                    'location': {
                        'latitude': self.location.get('lat', 0),
                        'longitude': self.location.get('lon', 0)
                    }
                }
                
                # Add to notifications collection to trigger Cloud Function
                self.db.collection('notifications').add(notification_data)
                
            except Exception as e:
                print(f"Failed to notify emergency contacts: {str(e)}")
                
    def show_dialog(self, title, text):
        """Show a popup dialog"""
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
        
    def on_leave(self):
        """Clean up when leaving the screen"""
        gps.stop()
        if self.current_emergency:
            self.cancel_sos()