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
        self.base_url = config.samsara.base_url
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
    
    async def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make API request to Samsara with retry logic for rate limiting
        """
        url = f"{self.base_url}{endpoint}"
        
        # Print request details for debugging
        print(f"Making Samsara API request to: {url}")
        print(f"Request parameters: {params}")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use synchronous requests in an async wrapper
                response = await asyncio.to_thread(
                    requests.get, url, headers=self.headers, params=params
                )
                
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    # Check for empty result
                    if not data or (isinstance(data, dict) and not data.get('data')):
                        print("Warning: API returned empty data")
                    return data
                elif response.status_code == 429:  # Rate limit exceeded
                    retry_after = float(response.headers.get('Retry-After', 10))
                    print(f"Rate limit exceeded. Retrying in {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    retry_count += 1
                else:
                    print(f"Error: {response.status_code}, {response.text}")
                    # Attempt to parse error response
                    try:
                        error_data = response.json()
                        print(f"Error details: {error_data}")
                    except:
                        pass
                        
                    # Retry for server errors (5xx)
                    if 500 <= response.status_code < 600:
                        retry_count += 1
                        await asyncio.sleep(2 * retry_count)  # Exponential backoff
                        continue
                    return {"data": [], "error": f"API Error: {response.status_code}"}
            except Exception as e:
                print(f"Request error: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2 * retry_count)  # Exponential backoff
                    continue
                return {"data": [], "error": f"Request error: {str(e)}"}
                
        # If we reached max retries
        return {"data": [], "error": "Max retries exceeded"}
    
    async def get_vehicle_locations(self, vehicle_ids: List[str] = None) -> Dict:
        """Get current GPS locations for vehicles with client-side filtering"""
        try:
            # Always request all vehicles and filter on the client side
            params = {"types": "gps"}
            
            if vehicle_ids and len(vehicle_ids) > 0:
                print(f"Will filter for vehicles: {vehicle_ids}")
            else:
                print("Requesting locations for all vehicles")
            
            # Make the API request
            response = await self._make_api_request("/fleet/vehicles/stats", params)
            
            # If we need to filter by specific vehicle IDs
            if vehicle_ids and len(vehicle_ids) > 0:
                # Handle both string and int IDs
                vehicle_id_set = set([str(id).strip() for id in vehicle_ids])
                
                # Filter the response data
                if 'data' in response:
                    filtered_data = [
                        vehicle for vehicle in response.get('data', [])
                        if str(vehicle.get('id', '')).strip() in vehicle_id_set
                    ]
                    
                    # Log how many vehicles were filtered
                    print(f"Filtered from {len(response.get('data', []))} vehicles to {len(filtered_data)} vehicles")
                    
                    # Replace the data array with our filtered results
                    response['data'] = filtered_data
                    
                    # If no matching vehicles found after filtering
                    if not filtered_data:
                        print(f"Warning: No vehicles found matching IDs: {vehicle_ids}")
                        print(f"Available vehicle IDs: {[v.get('id') for v in response.get('data', [])]}")
            
            return response
        except Exception as e:
            print(f"Error in get_vehicle_locations: {str(e)}")
            return {"data": []}

    async def get_vehicle_locations_feed(self, vehicle_ids: List[str] = None) -> Dict:
        """
        Get real-time location feed for specified vehicles with client-side filtering
        """
        try:
            # Request without filters
            params = {}
            
            if vehicle_ids and len(vehicle_ids) > 0:
                print(f"Will filter feed for vehicles: {vehicle_ids}")
            else:
                print("Requesting location feed for all vehicles")
            
            # Make the API request
            result = await self._make_api_request("/fleet/vehicles/locations/feed", params)
            
            # If we need to filter by specific vehicle IDs
            if vehicle_ids and len(vehicle_ids) > 0:
                # Handle both string and int IDs
                vehicle_id_set = set([str(id).strip() for id in vehicle_ids])
                
                # Filter the response data
                if 'data' in result:
                    original_count = len(result.get('data', []))
                    
                    filtered_data = [
                        vehicle for vehicle in result.get('data', [])
                        if str(vehicle.get('id', '')).strip() in vehicle_id_set
                    ]
                    
                    # Log how many vehicles were filtered
                    print(f"Filtered feed from {original_count} vehicles to {len(filtered_data)} vehicles")
                    
                    # Replace the data array with our filtered results
                    result['data'] = filtered_data
                    
                    # If no matching vehicles found after filtering
                    if not filtered_data:
                        print(f"Warning: No vehicles found in feed matching IDs: {vehicle_ids}")
                        if original_count > 0:
                            print(f"Available vehicle IDs in feed: {[v.get('id') for v in result.get('data', [])]}")
            
            # Add some debug info
            if result:
                vehicle_count = len(result.get("data", []))
                print(f"Final result: location feed data for {vehicle_count} vehicles")
            
            return result
        except Exception as e:
            print(f"Error in get_vehicle_locations_feed: {str(e)}")
            return {"data": []}
    
    async def get_vehicle_info(self, vehicle_id: str) -> Dict:
        """Get detailed information about a specific vehicle"""
        return await self._make_api_request(f"/fleet/vehicles/{vehicle_id}")
    
    async def get_driver_info(self, driver_id: str) -> Dict:
        """Get information about a specific driver"""
        return await self._make_api_request(f"/fleet/drivers/{driver_id}")
    
    async def get_all_vehicles(self) -> List[Dict]:
        """
        Get a list of all vehicles
        Uses the /fleet/vehicles endpoint directly
        """
        response = await self._make_api_request("/fleet/vehicles")
        return response.get("data", []) if response else []
    
    async def get_all_drivers(self) -> List[Dict]:
        """Get a list of all drivers"""
        response = await self._make_api_request("/fleet/drivers")
        return response.get("data", []) if response else []
    
    def format_location_for_email(self, location_data: Dict) -> str:
        """Format location data in a readable format for email responses"""
        vehicles = location_data.get("data", [])
        if not vehicles:
            return "No vehicle location data available."
        
        formatted_text = "Vehicle Locations:\n\n"
        
        for vehicle in vehicles:
            name = vehicle.get("name", "Unknown Vehicle")
            gps = vehicle.get("gps", {})
            
            # Check if we have actual GPS data for this vehicle
            if not gps or not all(key in gps for key in ["latitude", "longitude"]):
                formatted_text += f"- {name}: No GPS data available\n\n"
                continue
                
            latitude = gps.get("latitude")
            longitude = gps.get("longitude")
            time_stamp = gps.get("time", "Unknown")
            
            # Correctly extract the formatted location from the reverseGeo field
            reverse_geo = gps.get("reverseGeo", {})
            formatted_location = reverse_geo.get("formattedLocation", "No address available")
            
            map_link = f"https://maps.google.com/?q={latitude},{longitude}"
            formatted_text += f"- {name}:\n"
            formatted_text += f"  Time: {time_stamp}\n"
            formatted_text += f"  Location: {latitude}, {longitude}\n"
            formatted_text += f"  Address: {formatted_location}\n"
            formatted_text += f"  Google Maps: {map_link}\n\n"
        
        return formatted_text

    def format_location_feed_for_email(self, feed_data: Dict) -> str:
        """Format location feed data for email responses"""
        vehicles = feed_data.get("data", [])
        if not vehicles:
            return "No vehicle location feed data available."
        
        formatted_text = "Real-Time Vehicle Locations:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Unknown ID")
            name = vehicle.get("name", f"Vehicle {vehicle_id}")
            
            # Get locations array - may be empty
            locations = vehicle.get("locations", [])
            if not locations:
                formatted_text += f"- {name} (ID: {vehicle_id}): No location data available\n\n"
                continue
                
            # Get the most recent location entry
            location = locations[0] if locations else {}
            
            # Check if we have actual location data
            if not location or not all(key in location for key in ["latitude", "longitude"]):
                formatted_text += f"- {name} (ID: {vehicle_id}): No location data available\n\n"
                continue
                
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            time_stamp = location.get("time", "Unknown")
            
            # Correctly extract the formatted location from the reverseGeo field
            reverse_geo = location.get("reverseGeo", {})
            formatted_location = reverse_geo.get("formattedLocation", "No address available")
            
            map_link = f"https://maps.google.com/?q={latitude},{longitude}"
            formatted_text += f"- {name} (ID: {vehicle_id}):\n"
            formatted_text += f"  Time: {time_stamp}\n"
            formatted_text += f"  Location: {latitude}, {longitude}\n"
            formatted_text += f"  Address: {formatted_location}\n"
            formatted_text += f"  Speed: {location.get('speed', '0')} mph\n"
            formatted_text += f"  Heading: {location.get('heading', '0')}°\n"
            formatted_text += f"  Google Maps: {map_link}\n\n"
        
        return formatted_text
    
    def format_vehicle_info_for_email(self, vehicle_data: Dict) -> str:
        """Format vehicle information in a readable format for email responses"""
        vehicles = vehicle_data.get("data", [])
        if not vehicles:
            return "No vehicle information available."
        
        formatted_text = "Vehicle Information:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Not available")
            name = vehicle.get("name", "Not available")
            
            # Extract VIN and other data from externalIds
            external_ids = vehicle.get("externalIds", {})
            vin = external_ids.get("samsara.vin", "Not available")
            
            # Get additional details if available
            make = "VOLVO TRUCK"  # Default value, ideally would be extracted from actual data
            model = "Not available"
            year = "Not available"
            
            # If there's a VIN, we might be able to extract year from it
            if vin != "Not available" and len(vin) >= 10:
                # The 10th character of a VIN typically represents the model year
                year_char = vin[9]
                # This is a simplified mapping - real implementation would be more complex
                year_map = {
                    'A': '2010', 'B': '2011', 'C': '2012', 'D': '2013', 
                    'E': '2014', 'F': '2015', 'G': '2016', 'H': '2017',
                    'J': '2018', 'K': '2019', 'L': '2020', 'M': '2021',
                    'N': '2022', 'P': '2023', 'R': '2024', 'S': '2025'
                }
                year = year_map.get(year_char, "Not available")
            
            formatted_text += f"- ID: {vehicle_id}\n"
            formatted_text += f"- Name: {name}\n"
            formatted_text += f"- VIN: {vin}\n"
            formatted_text += f"- Make: {make}\n"
            formatted_text += f"- Model: {model}\n"
            formatted_text += f"- Year: {year}\n\n"
        
        return formatted_text