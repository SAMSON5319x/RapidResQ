import json
import uuid
import datetime
import aiohttp
import asyncio
from typing import Dict, List, Optional
import logging

class OfflineEAS:
    def __init__(self, config: Dict):
        """
        Initialize the Offline Emergency Alert System.
        
        Args:
            config (Dict): Configuration dictionary containing:
                - server_url: URL of the emergency alert server
                - api_key: API key for authentication
                - user_id: Identifier for the current user
        """
        self.server_url = config['server_url']
        self.api_key = config['api_key']
        self.user_id = config['user_id']
        self.storage_file = 'offline_eas_alerts.json'
        self.logger = logging.getLogger(__name__)
        
    async def send_emergency_alert(self, alert_data: Dict) -> Dict:
        """
        Send an emergency alert, storing it offline if there's no connection.
        
        Args:
            alert_data (Dict): Data containing alert information
            
        Returns:
            Dict: Response containing success status and alert ID
        """
        alert = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.datetime.now().isoformat(),
            'user_id': self.user_id,
            **alert_data,
            'status': 'pending'
        }
        
        try:
            # Attempt to send to server first
            return await self.send_to_server(alert)
        except Exception as e:
            self.logger.error(f"Failed to send alert to server: {e}")
            return await self.store_offline(alert)
    
    async def store_offline(self, alert: Dict) -> Dict:
        """
        Store alert data in local storage when offline.
        
        Args:
            alert (Dict): Alert data to store
            
        Returns:
            Dict: Status of storage operation
        """
        try:
            alerts = await self.get_pending_alerts()
            alerts.append(alert)
            
            with open(self.storage_file, 'w') as f:
                json.dump(alerts, f)
                
            return {
                'success': True,
                'message': 'Alert stored offline',
                'alert_id': alert['id']
            }
        except Exception as e:
            self.logger.error(f"Error storing offline alert: {e}")
            return {
                'success': False,
                'message': 'Failed to store alert offline',
                'error': str(e)
            }
    
    async def send_to_server(self, alert: Dict) -> Dict:
        """
        Send alert to the emergency alert server.
        
        Args:
            alert (Dict): Alert data to send
            
        Returns:
            Dict: Server response
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/emergency-alerts",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                },
                json=alert
            ) as response:
                if response.status != 200:
                    raise Exception('Server response was not ok')
                    
                return {
                    'success': True,
                    'message': 'Alert sent successfully',
                    'alert_id': alert['id']
                }
    
    async def sync_offline_alerts(self) -> List[Dict]:
        """
        Synchronize stored offline alerts with the server.
        
        Returns:
            List[Dict]: Results of synchronization attempts
        """
        try:
            alerts = await self.get_pending_alerts()
            if not alerts:
                return []
            
            sync_results = []
            for alert in alerts:
                try:
                    result = await self.send_to_server(alert)
                    sync_results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to sync alert {alert['id']}: {e}")
                    continue
            
            # Update storage with remaining unsent alerts
            remaining_alerts = [
                alert for alert in alerts
                if not any(result['alert_id'] == alert['id'] for result in sync_results)
            ]
            
            if remaining_alerts:
                with open(self.storage_file, 'w') as f:
                    json.dump(remaining_alerts, f)
            else:
                # All alerts synced, remove storage file
                import os
                if os.path.exists(self.storage_file):
                    os.remove(self.storage_file)
            
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Error syncing offline alerts: {e}")
            return {
                'success': False,
                'message': 'Failed to sync offline alerts',
                'error': str(e)
            }
    
    async def get_pending_alerts(self) -> List[Dict]:
        """
        Retrieve all pending offline alerts.
        
        Returns:
            List[Dict]: List of pending alerts
        """
        try:
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                return []
        except Exception as e:
            self.logger.error(f"Error getting pending alerts: {e}")
            return []