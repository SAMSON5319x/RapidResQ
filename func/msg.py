import platform
import requests
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, Optional

class SMSService:
    def __init__(self, config: Dict):
        """
        Initialize SMS Service with configuration
        
        Args:
            config (Dict): Configuration containing:
                - server_url: URL to send message data
                - api_key: Server authentication key
        """
        self.server_url = config['server_url']
        self.api_key = config['api_key']
        self.platform = platform.system()  # Detect OS: 'Darwin' for iOS, 'Linux' for Android
        self.logger = logging.getLogger(__name__)
        
    def send_message(self, phone_number: str, message: str) -> Dict:
        """
        Send SMS message based on platform
        
        Args:
            phone_number (str): Recipient's phone number
            message (str): Message content
            
        Returns:
            Dict: Status of the message sending operation
        """
        try:
            if self.platform == 'Linux':  # Android
                return self._send_android_sms(phone_number, message)
            elif self.platform == 'Darwin':  # iOS
                return self._send_ios_sms(phone_number, message)
            else:
                raise Exception(f"Unsupported platform: {self.platform}")
                
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send SMS: {str(e)}'
            }

    def _send_android_sms(self, phone_number: str, message: str) -> Dict:
        """
        Send SMS on Android using termux-sms-send
        
        Args:
            phone_number (str): Recipient's phone number
            message (str): Message content
            
        Returns:
            Dict: Status of the sending operation
        """
        try:
            # Use termux-sms-send for Android
            cmd = ['termux-sms-send', '-n', phone_number, message]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                message_data = {
                    'phone_number': phone_number,
                    'message': message,
                    'platform': 'android',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'sent'
                }
                
                # Log to server
                server_response = self._log_to_server(message_data)
                
                return {
                    'success': True,
                    'message': 'SMS sent successfully on Android',
                    'server_response': server_response
                }
            else:
                raise Exception(f"SMS send failed: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Android SMS error: {str(e)}")

    def _send_ios_sms(self, phone_number: str, message: str) -> Dict:
        """
        Send SMS on iOS using osascript
        
        Args:
            phone_number (str): Recipient's phone number
            message (str): Message content
            
        Returns:
            Dict: Status of the sending operation
        """
        try:
            # AppleScript command to send SMS
            script = f'''
            tell application "Messages"
                send "{message}" to buddy "{phone_number}" of service "SMS"
            end tell
            '''
            
            cmd = ['osascript', '-e', script]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                message_data = {
                    'phone_number': phone_number,
                    'message': message,
                    'platform': 'ios',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'sent'
                }
                
                # Log to server
                server_response = self._log_to_server(message_data)
                
                return {
                    'success': True,
                    'message': 'SMS sent successfully on iOS',
                    'server_response': server_response
                }
            else:
                raise Exception(f"SMS send failed: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"iOS SMS error: {str(e)}")

    def _log_to_server(self, message_data: Dict) -> Dict:
        """
        Log message details to server
        
        Args:
            message_data (Dict): Message information to log
            
        Returns:
            Dict: Server response
        """
        try:
            response = requests.post(
                f"{self.server_url}/messages",
                json=message_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Server logging failed: {str(e)}")
            raise Exception(f"Failed to log message to server: {str(e)}")

    def get_message_status(self, message_id: str) -> Dict:
        """
        Get status of a sent message from server
        
        Args:
            message_id (str): ID of the message to check
            
        Returns:
            Dict: Message status information
        """
        try:
            response = requests.get(
                f"{self.server_url}/messages/{message_id}",
                headers={
                    'Authorization': f'Bearer {self.api_key}'
                }
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Status check failed: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get message status: {str(e)}'
            }

    def get_device_messages(self) -> Dict:
        """
        Get messages from device based on platform
        
        Returns:
            Dict: List of messages or error information
        """
        try:
            if self.platform == 'Linux':  # Android
                cmd = ['termux-sms-list']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    return {
                        'success': True,
                        'messages': json.loads(result.stdout)
                    }
            elif self.platform == 'Darwin':  # iOS
                script = '''
                tell application "Messages"
                    get every message
                end tell
                '''
                cmd = ['osascript', '-e', script]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    return {
                        'success': True,
                        'messages': result.stdout.split('\n')
                    }
                    
            return {
                'success': False,
                'message': 'Failed to get device messages'
            }
            
        except Exception as e:
            self.logger.error(f"Get messages failed: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get messages: {str(e)}'
            }