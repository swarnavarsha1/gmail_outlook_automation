# src/tools/SamsaraTools.py
import requests
import time
import asyncio
from typing import Dict, List, Any, Optional
from config import config_manager

class SamsaraTools:
    """Class to interact with Samsara API with built-in rate limiting handling"""
    
    def __init__(self):
        config = config_manager.get_config()
        self.api_token = config.samsara.api_token
        self.base_url = config.samsara.base_url or "https://api.samsara.com"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
    
    async def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make API request to Samsara with retry logic for rate limiting
        """
        url = f"{self.base_url}{endpoint}"
        
        while True:
            try:
                # Use synchronous requests in an async wrapper
                response = await asyncio.to_thread(
                    requests.get, url, headers=self.headers, params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit exceeded
                    retry_after = float(response.headers.get('Retry-After', 10))
                    print(f"Rate limit exceeded. Retrying in {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"Error: {response.status_code}, {response.text}")
                    return None
            except Exception as e:
                print(f"Request error: {str(e)}")
                return None
    
    async def get_vehicle_locations(self, vehicle_ids: List[str] = None) -> Dict:
        """Get current GPS locations for vehicles"""
        params = {"types": "gps"}
        if vehicle_ids:
            params["vehicles"] = ",".join(vehicle_ids)
        
        return await self._make_api_request("/fleet/vehicles/stats", params)
    
    async def get_vehicle_info(self, vehicle_id: str) -> Dict:
        """Get detailed information about a specific vehicle"""
        return await self._make_api_request(f"/fleet/vehicles/{vehicle_id}")
    
    async def get_driver_info(self, driver_id: str) -> Dict:
        """Get information about a specific driver"""
        return await self._make_api_request(f"/fleet/drivers/{driver_id}")
    
    async def get_all_vehicles(self) -> List[Dict]:
        """Get a list of all vehicles"""
        # Using the specified URL from the requirements
        response = await self._make_api_request("/fleet/vehicles")
        return response.get("data", []) if response else []
    
    async def get_all_drivers(self) -> List[Dict]:
        """Get a list of all drivers"""
        response = await self._make_api_request("/fleet/drivers")
        return response.get("data", []) if response else []
    
    # Helper methods for formatting data for emails
    def format_location_for_email(self, location_data: Dict) -> str:
        """Format location data in a readable format for email responses"""
        vehicles = location_data.get("data", [])
        if not vehicles:
            return "No vehicle location data available."
        
        formatted_text = "Vehicle Locations:\n\n"
        
        for vehicle in vehicles:
            name = vehicle.get("name", "Unknown Vehicle")
            gps = vehicle.get("gps", {})
            
            latitude = gps.get("latitude")
            longitude = gps.get("longitude")
            
            if latitude and longitude:
                map_link = f"https://maps.google.com/?q={latitude},{longitude}"
                formatted_text += f"- {name}:\n"
                formatted_text += f"  Location: {latitude}, {longitude}\n"
                formatted_text += f"  Google Maps: {map_link}\n"
                formatted_text += f"  Last Updated: {gps.get('time', 'Unknown')}\n\n"
            else:
                formatted_text += f"- {name}: No GPS data available\n\n"
        
        return formatted_text