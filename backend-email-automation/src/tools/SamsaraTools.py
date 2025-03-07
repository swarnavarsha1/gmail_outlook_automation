# src/tools/SamsaraTools.py
import requests
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from config import config_manager

logger = logging.getLogger(__name__)

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
        logger.debug(f"Making Samsara API request to: {url}")
        logger.debug(f"Request parameters: {params}")
        
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
            # Build parameters with vehicle IDs if provided
            params = {}
            if vehicle_ids and len(vehicle_ids) > 0:
                # Join vehicle IDs with commas for the API
                vehicle_ids_param = ",".join([str(id).strip() for id in vehicle_ids])
                params["vehicleIds"] = vehicle_ids_param
                print(f"Requesting location feed for vehicles: {vehicle_ids_param}")
            else:
                print("Requesting location feed for all vehicles")
            
            # Make the API request
            result = await self._make_api_request("/fleet/vehicles/locations/feed", params)
            
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

    # NEW METHODS FOR ADDITIONAL ENDPOINTS
    
    async def get_vehicle_driver_assignments(self, vehicle_ids: List[str] = None) -> Dict:
        """
        Get driver assignments for vehicles
        Endpoint: /fleet/vehicles/driver-assignments
        """
        try:
            params = {}
            if vehicle_ids and len(vehicle_ids) > 0:
                # For a single vehicle ID
                if len(vehicle_ids) == 1:
                    params["vehicleIds"] = str(vehicle_ids[0]).strip()
                # For multiple vehicle IDs
                else:
                    params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
            
            return await self._make_api_request("/fleet/vehicles/driver-assignments", params)
        except Exception as e:
            print(f"Error in get_vehicle_driver_assignments: {str(e)}")
            return {"data": []}
    
    async def get_vehicle_immobilizer_stream(self, vehicle_ids: List[str] = None, start_time: str = None) -> Dict:
        """
        Get vehicle immobilizer stream
        Endpoint: /fleet/vehicles/immobilizer/stream
        """
        try:
            params = {}
            if start_time:
                params["startTime"] = start_time
                
            if vehicle_ids and len(vehicle_ids) > 0:
                params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
            
            return await self._make_api_request("/fleet/vehicles/immobilizer/stream", params)
        except Exception as e:
            print(f"Error in get_vehicle_immobilizer_stream: {str(e)}")
            return {"data": []}
    
    async def get_location_history(self, 
                              vehicle_ids: List[str], 
                              start_time: str, 
                              end_time: str) -> Dict:
        """
        Get historical location data for vehicles
        Endpoint: /fleet/vehicles/locations/history
        """
        try:
            params = {
                "startTime": start_time,
                "endTime": end_time
            }
            
            if vehicle_ids and len(vehicle_ids) > 0:
                params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
            
            return await self._make_api_request("/fleet/vehicles/locations/history", params)
        except Exception as e:
            print(f"Error in get_location_history: {str(e)}")
            return {"data": []}
    
    async def get_vehicle_stats_feed(self, 
                               vehicle_ids: List[str] = None, 
                               types: List[str] = None) -> Dict:
        """
        Get vehicle stats feed for specific metrics
        Endpoint: /fleet/vehicles/stats/feed
        """
        try:
            params = {}
            
            if vehicle_ids and len(vehicle_ids) > 0:
                params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
                
            if types and len(types) > 0:
                params["types"] = ",".join(types)
            else:
                # Default types if none specified
                params["types"] = "spreaderGranularName,evChargingCurrentMilliAmp"
            
            return await self._make_api_request("/fleet/vehicles/stats/feed", params)
        except Exception as e:
            print(f"Error in get_vehicle_stats_feed: {str(e)}")
            return {"data": []}
    
    async def get_vehicle_stats_history(self, 
                                  vehicle_ids: List[str], 
                                  start_time: str, 
                                  end_time: str,
                                  types: List[str] = None) -> Dict:
        """
        Get historical vehicle stats
        Endpoint: /fleet/vehicles/stats/history
        """
        try:
            params = {
                "startTime": start_time,
                "endTime": end_time
            }
            
            if vehicle_ids and len(vehicle_ids) > 0:
                params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
                
            if types and len(types) > 0:
                params["types"] = ",".join(types)
            else:
                # Default types if none specified
                params["types"] = "spreaderGranularName,evChargingCurrentMilliAmp"
            
            return await self._make_api_request("/fleet/vehicles/stats/history", params)
        except Exception as e:
            print(f"Error in get_vehicle_stats_history: {str(e)}")
            return {"data": []}
    
    async def get_tachograph_files_history(self, 
                                    vehicle_ids: List[str], 
                                    start_time: str, 
                                    after: str = None) -> Dict:
        """
        Get tachograph file history for vehicles
        Endpoint: /fleet/vehicles/tachograph-files/history
        """
        try:
            params = {
                "startTime": start_time
            }
            
            if after:
                params["after"] = after
                
            if vehicle_ids and len(vehicle_ids) > 0:
                params["vehicleIds"] = ",".join([str(id).strip() for id in vehicle_ids])
            
            return await self._make_api_request("/fleet/vehicles/tachograph-files/history", params)
        except Exception as e:
            print(f"Error in get_tachograph_files_history: {str(e)}")
            return {"data": []}
    
    # ADDITIONAL FORMATTER METHODS FOR NEW DATA TYPES
    
    def format_driver_assignments_for_email(self, assignments_data: Dict) -> str:
        """Format driver assignment data for email responses"""
        vehicles = assignments_data.get("data", [])
        if not vehicles:
            return "No driver assignment data available."
        
        formatted_text = "Vehicle Driver Assignments:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Unknown")
            vehicle_name = vehicle.get("name", f"Vehicle {vehicle_id}")
            
            assignments = vehicle.get("driverAssignments", [])
            if not assignments:
                formatted_text += f"- {vehicle_name} (ID: {vehicle_id}): No driver assigned\n\n"
                continue
            
            # Get the most recent assignment (first in the list)
            assignment = assignments[0]
            driver = assignment.get("driver", {})
            driver_id = driver.get("id", "Unassigned")
            driver_name = driver.get("name", "No driver assigned")
            
            formatted_text += f"- {vehicle_name} (ID: {vehicle_id}):\n"
            formatted_text += f"  Driver: {driver_name}\n"
            formatted_text += f"  Driver ID: {driver_id}\n"
            
            # Add assignment details if available
            start_time = assignment.get("startTime")
            if start_time:
                formatted_text += f"  Assigned since: {start_time}\n"
                
            is_passenger = assignment.get("isPassenger", False)
            if is_passenger:
                formatted_text += f"  Role: Passenger\n"
            else:
                formatted_text += f"  Role: Driver\n"
            
            formatted_text += "\n"
        
        return formatted_text
    
    def format_immobilizer_data_for_email(self, immobilizer_data: Dict) -> str:
        """Format immobilizer data for email responses"""
        vehicles = immobilizer_data.get("data", [])
        if not vehicles:
            return "No immobilizer data available."
        
        formatted_text = "Vehicle Immobilizer Status:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Unknown")
            name = vehicle.get("name", f"Vehicle {vehicle_id}")
            
            immobilizer = vehicle.get("immobilizer", {})
            is_immobilized = immobilizer.get("isImmobilized", False)
            last_updated = immobilizer.get("updatedAtTime", "Unknown")
            
            status = "IMMOBILIZED" if is_immobilized else "MOBILE"
            
            formatted_text += f"- {name} (ID: {vehicle_id}):\n"
            formatted_text += f"  Status: {status}\n"
            formatted_text += f"  Last Updated: {last_updated}\n\n"
        
        return formatted_text
    
    def format_location_history_for_email(self, history_data: Dict) -> str:
        """Format location history data for email responses"""
        vehicles = history_data.get("data", [])
        if not vehicles:
            return "No location history data available."
        
        formatted_text = "Vehicle Location History:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Unknown")
            name = vehicle.get("name", f"Vehicle {vehicle_id}")
            
            # Get locations array - may be empty
            locations = vehicle.get("locations", [])
            if not locations:
                formatted_text += f"- {name} (ID: {vehicle_id}): No location history available\n\n"
                continue
                
            formatted_text += f"- {name} (ID: {vehicle_id}):\n"
            
            # Limit to 5 most recent locations to avoid excessively long emails
            max_locations = min(5, len(locations))
            for i in range(max_locations):
                location = locations[i]
                latitude = location.get("latitude", "N/A")
                longitude = location.get("longitude", "N/A")
                time_stamp = location.get("time", "Unknown")
                
                formatted_text += f"  [{i+1}] Time: {time_stamp}\n"
                formatted_text += f"      Location: {latitude}, {longitude}\n"
                
                # Add address if available
                reverse_geo = location.get("reverseGeo", {})
                if reverse_geo and "formattedLocation" in reverse_geo:
                    formatted_text += f"      Address: {reverse_geo['formattedLocation']}\n"
                
                # Add Google Maps link
                formatted_text += f"      Maps: https://maps.google.com/?q={latitude},{longitude}\n"
            
            if len(locations) > max_locations:
                formatted_text += f"  ... and {len(locations) - max_locations} more locations\n"
            
            formatted_text += "\n"
        
        return formatted_text
    
    def format_vehicle_stats_for_email(self, stats_data: Dict) -> str:
        """Format vehicle stats data for email responses"""
        vehicles = stats_data.get("data", [])
        if not vehicles:
            return "No vehicle stats data available."
        
        formatted_text = "Vehicle Stats Information:\n\n"
        
        for vehicle in vehicles:
            vehicle_id = vehicle.get("id", "Unknown")
            name = vehicle.get("name", f"Vehicle {vehicle_id}")
            
            formatted_text += f"- {name} (ID: {vehicle_id}):\n"
            
            # Process each stat type
            for stat_type, stat_value in vehicle.items():
                # Skip id and name
                if stat_type in ["id", "name"]:
                    continue
                
                # Format the stat based on type
                if stat_type == "evChargingCurrentMilliAmp":
                    value = f"{int(stat_value) / 1000:.2f} Amps" if isinstance(stat_value, (int, float)) else "N/A"
                    formatted_text += f"  EV Charging Current: {value}\n"
                elif stat_type == "spreaderGranularName":
                    formatted_text += f"  Spreader Granular: {stat_value}\n"
                else:
                    # Generic formatting for other stat types
                    formatted_name = ' '.join(word.capitalize() for word in stat_type.split('_'))
                    formatted_text += f"  {formatted_name}: {stat_value}\n"
            
            formatted_text += "\n"
        
        return formatted_text
    
    def format_tachograph_files_for_email(self, tachograph_data: Dict) -> str:
        """Format tachograph files data for email responses"""
        files = tachograph_data.get("data", [])
        if not files:
            return "No tachograph files available."
        
        formatted_text = "Tachograph Files:\n\n"
        
        for file in files:
            vehicle_id = file.get("vehicleId", "Unknown")
            vehicle_name = file.get("vehicleName", f"Vehicle {vehicle_id}")
            
            file_id = file.get("id", "Unknown")
            file_type = file.get("fileType", "Unknown")
            start_time = file.get("startTime", "Unknown")
            end_time = file.get("endTime", "Unknown")
            
            formatted_text += f"- {vehicle_name} (ID: {vehicle_id}):\n"
            formatted_text += f"  File ID: {file_id}\n"
            formatted_text += f"  Type: {file_type}\n"
            formatted_text += f"  Period: {start_time} to {end_time}\n\n"
        
        return formatted_text
    
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
    
    def format_vehicle_info_for_email(self, vehicle_data: Dict, driver_assignments_data: Dict = None) -> str:
        """Format vehicle information in a readable format for email responses, including driver info"""
        vehicles = vehicle_data.get("data", [])
        if not vehicles:
            return "No vehicle information available."
        
        formatted_text = "Vehicle Information:\n\n"
        
        # Create driver lookup dictionary if driver assignments are provided
        driver_lookup = {}
        if driver_assignments_data:
            for assignment in driver_assignments_data.get("data", []):
                vehicle_id = str(assignment.get("id", ""))
                
                # Check for driverAssignments array
                driver_assignments = assignment.get("driverAssignments", [])
                if driver_assignments and len(driver_assignments) > 0:
                    driver = driver_assignments[0].get("driver", {})
                    if vehicle_id and driver:
                        driver_lookup[vehicle_id] = {
                            "name": driver.get("name", "Not assigned"),
                            "id": driver.get("id", ""),
                            "assigned_since": driver_assignments[0].get("startTime", "Unknown")
                        }
        
        for vehicle in vehicles:
            vehicle_id = str(vehicle.get("id", "Not available"))
            name = vehicle.get("name", "Not available")
            
            # Extract vehicle details - first try from the vehicle object directly
            make = vehicle.get("make", "Not available")
            if make == "Not available":  # Default fallback
                make = "VOLVO TRUCK"
                
            model = vehicle.get("model", "Not available")
            year = vehicle.get("year", "Not available")
            
            # Extract VIN either from direct property or from externalIds
            vin = vehicle.get("vin", "Not available")
            if vin == "Not available" and "externalIds" in vehicle:
                external_ids = vehicle.get("externalIds", {})
                vin = external_ids.get("samsara.vin", "Not available")
            
            # Get license plate if available
            license_plate = vehicle.get("licensePlate", "Not available")
            
            # Look for static assigned driver first
            driver_name = "Not assigned"
            driver_id = ""
            static_driver = vehicle.get("staticAssignedDriver", {})
            if static_driver:
                driver_name = static_driver.get("name", "Not assigned")
                driver_id = static_driver.get("id", "")
            
            # If no static driver, check the driver assignments lookup
            if driver_name == "Not assigned" and vehicle_id in driver_lookup:
                driver_info = driver_lookup.get(vehicle_id, {})
                driver_name = driver_info.get("name", "Not assigned")
                driver_id = driver_info.get("id", "")
            
            formatted_text += f"- ID: {vehicle_id}\n"
            formatted_text += f"- Name: {name}\n"
            formatted_text += f"- VIN: {vin}\n"
            formatted_text += f"- Make: {make}\n"
            formatted_text += f"- Model: {model}\n"
            formatted_text += f"- Year: {year}\n"
            
            # Add license plate if available
            if license_plate != "Not available":
                formatted_text += f"- License Plate: {license_plate}\n"
            
            # Add driver information
            formatted_text += f"- Assigned Driver: {driver_name}\n"
            if driver_id:
                formatted_text += f"- Driver ID: {driver_id}\n"
            
            formatted_text += "\n"
        
        return formatted_text