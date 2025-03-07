from enum import Enum
import traceback
from colorama import Fore, Style
from .agents import Agents
import dns.resolver
from config import config_manager
from typing import Optional, Tuple
from .state import GraphState, Email
from .tools.GmailTools import GmailToolsClass
from .tools.enhanced_outlook_tools import EnhancedOutlookTools
from .tools.SamsaraTools import SamsaraTools

class EmailServiceType(Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"

class EmailServiceDetector:
    """Detects the type of email service based on email address and MX records"""
    
    @staticmethod
    def check_mx_records(domain: str) -> Optional[EmailServiceType]:
        """
        Check MX records to determine email service
        Returns EmailServiceType or None if undetermined
        """
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            
            # Convert MX records to lowercase strings for easier matching
            mx_domains = [str(mx.exchange).lower() for mx in mx_records]
            
            # Google Workspace MX patterns
            google_mx_patterns = [
                'aspmx.l.google.com',
                'googlemail.com',
                'google.com',
                'alt1.aspmx.l.google.com',
                'alt2.aspmx.l.google.com'
            ]
            
            # Office 365 MX patterns
            office365_mx_patterns = [
                'protection.outlook.com',
                'mail.protection.outlook.com',
                'onmicrosoft.com'
            ]
            
            # Check for Google Workspace
            if any(any(pattern in mx for pattern in google_mx_patterns) for mx in mx_domains):
                return EmailServiceType.GMAIL
                
            # Check for Office 365
            if any(any(pattern in mx for pattern in office365_mx_patterns) for mx in mx_domains):
                return EmailServiceType.OUTLOOK
                
            return None
            
        except Exception as e:
            return None

    @staticmethod
    def detect_service(email_address: str) -> Tuple[EmailServiceType, Optional[str]]:
        """
        Detects email service type and returns with any warning message
        Returns: (service_type, warning_message)
        """
        email_domain = email_address.lower().split('@')[1]
        warning = None
        
        # Check if email is in configured Gmail accounts
        gmail_accounts = config_manager.get_config().gmail_accounts
        for account in gmail_accounts:
            if account.email.lower() == email_address.lower():
                return EmailServiceType.GMAIL, None
        
        # Check if email is in configured Outlook accounts
        outlook_accounts = config_manager.get_config().outlook_accounts
        for account in outlook_accounts:
            if account.email.lower() == email_address.lower():
                return EmailServiceType.OUTLOOK, None
        
        # If not directly found in config, try MX record detection
        service_type = EmailServiceDetector.check_mx_records(email_domain)
        
        if service_type:
            # Validate credentials for detected service
            if service_type == EmailServiceType.GMAIL and not EmailServiceDetector.is_valid_credentials(service_type, email_address):
                warning = f"Gmail credentials not properly configured for {email_address}"
            elif service_type == EmailServiceType.OUTLOOK and not EmailServiceDetector.is_valid_credentials(service_type, email_address):
                warning = f"Outlook credentials not properly configured for {email_address}"
            return service_type, warning
            
        # If MX records don't give a clear answer, use domain patterns
        if email_domain.endswith('.in'):
            service_type = EmailServiceType.GMAIL
        elif email_domain.endswith('.cloud'):
            service_type = EmailServiceType.OUTLOOK
        else:
            # Default to available service
            if EmailServiceDetector.is_valid_credentials(EmailServiceType.GMAIL):
                service_type = EmailServiceType.GMAIL
                warning = "Defaulting to Gmail for unknown domain"
            elif EmailServiceDetector.is_valid_credentials(EmailServiceType.OUTLOOK):
                service_type = EmailServiceType.OUTLOOK
                warning = "Defaulting to Office 365 for unknown domain"
            else:
                raise ValueError("No valid email service credentials configured")
        
        # Validate credentials
        if not EmailServiceDetector.is_valid_credentials(service_type):
            warning = f"{service_type.value} credentials not properly configured"
            
        return service_type, warning

    @staticmethod
    def is_valid_credentials(service_type: EmailServiceType, email_address: str = None) -> bool:
        """Check if required credentials are available for the service and specific email"""
        if service_type == EmailServiceType.GMAIL:
            if email_address:
                account = config_manager.get_gmail_account(email_address)
                return bool(account and account.credentials_file)
            else:
                return any(account.credentials_file for account in config_manager.get_config().gmail_accounts)
        elif service_type == EmailServiceType.OUTLOOK:
            if email_address:
                account = config_manager.get_outlook_account(email_address)
                return bool(account and account.client_id and account.client_secret and account.tenant_id)
            else:
                return any(
                    account.client_id and account.client_secret and account.tenant_id 
                    for account in config_manager.get_config().outlook_accounts
                )
        return False

class EmailTools:
    """Unified interface for email operations"""
    def __init__(self, email_address: str):
        self.email_address = email_address
        service_type, warning = EmailServiceDetector.detect_service(email_address)
        self.service_type = service_type
        
        if warning:
            print(f"{Fore.YELLOW}Warning: {warning}{Style.RESET_ALL}")
        
        if self.service_type == EmailServiceType.GMAIL:
            self.service = GmailToolsClass(email_address)
        else:
            self.service = EnhancedOutlookTools(email_address)

    async def fetch_unanswered_emails(self, max_results=50):
        """Fetch unanswered emails from either service"""
        try:
            return await self.service.fetch_unanswered_emails(max_results)
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    async def create_draft_reply(self, initial_email, reply_text):
        """Create draft reply in either service"""
        try:
            return await self.service.create_draft_reply(initial_email, reply_text)
        except Exception as e:
            print(f"Error creating draft: {e}")
            return None

    async def send_reply(self, initial_email, reply_text):
        """Send reply using either service"""
        try:
            return await self.service.send_reply(initial_email, reply_text)
        except Exception as e:
            print(f"Error sending reply: {e}")
            return None

    async def fetch_draft_replies(self):
        """Fetch draft replies from either service"""
        try:
            return await self.service.fetch_draft_replies()
        except Exception as e:
            print(f"Error fetching drafts: {e}")
            return []
        
    async def cleanup(self):
        """Cleanup resources for the current email service"""
        if hasattr(self.service, 'cleanup'):
            await self.service.cleanup()

class Nodes:
    def __init__(self, email_address: str):
        """Initialize Nodes with email service detection"""
        self.agents = Agents()
        self.email_address = email_address
        self.email_tools = EmailTools(email_address)
        self.samsara_tools = SamsaraTools()
        print(f"{Fore.CYAN}Initialized email service: {self.email_tools.service_type.value} for {email_address}{Style.RESET_ALL}")

    async def load_new_emails(self, state: GraphState) -> GraphState:
        """Load new emails from configured provider"""
        print(Fore.YELLOW + f"Loading new emails for {self.email_address} ({self.email_tools.service_type.value})...\n" + Style.RESET_ALL)
        try:
            emails = await self.email_tools.fetch_unanswered_emails()
            if not emails:
                return {"emails": []}
            return {"emails": [Email(**email) for email in emails]}
        except Exception as e:
            print(Fore.RED + f"Error loading emails: {str(e)}" + Style.RESET_ALL)
            return {"emails": []}

    def check_new_emails(self, state: GraphState) -> str:
        """Check if there are new emails to process"""
        if len(state['emails']) == 0:
            print(Fore.RED + "No new emails to process" + Style.RESET_ALL)
            return "empty"
        print(Fore.GREEN + f"Found {len(state['emails'])} new emails to process" + Style.RESET_ALL)
        return "process"

    def is_email_inbox_empty(self, state: GraphState) -> GraphState:
        """Check if email inbox is empty"""
        return state

    def categorize_email(self, state: GraphState) -> GraphState:
        """Categorizes the current email using the categorize_email agent."""
        print(Fore.YELLOW + "Checking email category...\n" + Style.RESET_ALL)
        
        if not state["emails"]:  # Check if there are any emails to process
            return {
                "email_category": "",
                "current_email": None
            }
        
        # Get the last email
        current_email = state["emails"][-1]
        result = self.agents.categorize_email.invoke({"email": current_email.body})
        print(Fore.MAGENTA + f"Email category: {result.category.value}" + Style.RESET_ALL)
        
        return {
            "email_category": result.category.value,
            "current_email": current_email
        }

    def route_email_based_on_category(self, state: GraphState) -> str:
        """Routes the email based on its category."""
        print(Fore.YELLOW + "Routing email based on category...\n" + Style.RESET_ALL)
        category = state["email_category"]
        if category == "product_enquiry":
            return "product related"
        elif category in ["samsara_location_query", "samsara_driver_query", "samsara_vehicle_query"]:
            return "samsara related"
        elif category == "unrelated":
            return "unrelated"
        else:
            return "not product related"

    def construct_rag_queries(self, state: GraphState) -> GraphState:
        """Constructs RAG queries based on the email content."""
        print(Fore.YELLOW + "Designing RAG query...\n" + Style.RESET_ALL)
        email_content = state["current_email"].body
        query_result = self.agents.design_rag_queries.invoke({"email": email_content})
        
        return {"rag_queries": query_result.queries}

    def retrieve_from_rag(self, state: GraphState) -> GraphState:
        """Retrieves information from internal knowledge based on RAG questions."""
        print(Fore.YELLOW + "Retrieving information from internal knowledge...\n" + Style.RESET_ALL)
        final_answer = ""
        for query in state["rag_queries"]:
            rag_result = self.agents.generate_rag_answer.invoke(query)
            final_answer += query + "\n" + rag_result + "\n\n"
        
        return {"retrieved_documents": final_answer}

    def write_draft_email(self, state: GraphState) -> GraphState:
        """Writes a draft email based on the current email and retrieved information."""
        print(Fore.YELLOW + "Writing draft email...\n" + Style.RESET_ALL)
        
        # Format input to the writer agent
        inputs = (
            f'# **EMAIL CATEGORY:** {state["email_category"]}\n\n'
            f'# **EMAIL CONTENT:**\n{state["current_email"].body}\n\n'
            f'# **INFORMATION:**\n{state.get("retrieved_documents", "")}' # Empty for feedback or complaint
        )
        
        # Get messages history for current email
        writer_messages = state.get('writer_messages', [])
        
        # Write email
        draft_result = self.agents.email_writer.invoke({
            "email_information": inputs,
            "history": writer_messages
        })
        email = draft_result.email
        trials = state.get('trials', 0) + 1

        # Append writer's draft to the message list
        writer_messages.append(f"**Draft {trials}:**\n{email}")

        return {
            "generated_email": email, 
            "trials": trials,
            "writer_messages": writer_messages
        }

    def verify_generated_email(self, state: GraphState) -> GraphState:
        """Verifies the generated email using the proofreader agent."""
        print(Fore.YELLOW + "Verifying generated email...\n" + Style.RESET_ALL)
        review = self.agents.email_proofreader.invoke({
            "initial_email": state["current_email"].body,
            "generated_email": state["generated_email"],
        })

        writer_messages = state.get('writer_messages', [])
        writer_messages.append(f"**Proofreader Feedback:**\n{review.feedback}")

        return {
            "sendable": review.send,
            "writer_messages": writer_messages
        }

    def must_rewrite(self, state: GraphState) -> str:
        """Determines if the email needs to be rewritten based on the review and trial count."""
        email_sendable = state["sendable"]
        if email_sendable:
            print(Fore.GREEN + "Email is good, ready to be sent!!!" + Style.RESET_ALL)
            state["emails"].pop()  
            state["writer_messages"] = []
            return "send"
        elif state["trials"] >= 3:
            print(Fore.RED + "Email is not good, we reached max trials must stop!!!" + Style.RESET_ALL)
            state["emails"].pop()  
            state["writer_messages"] = []
            if len(state["emails"]) > 0:
                return "process" 
            return "empty"  
        else:
            print(Fore.RED + "Email is not good, must rewrite it..." + Style.RESET_ALL)
            return "rewrite"
        
    def identify_samsara_query(self, state: GraphState) -> GraphState:
        """Identifies the specific Samsara query in the email."""
        print(Fore.YELLOW + "Identifying Samsara query type...\n" + Style.RESET_ALL)
        email_content = state["current_email"].body
        query_result = self.agents.identify_samsara_query.invoke({"email": email_content})
        
        print(Fore.MAGENTA + f"Samsara query type: {query_result.query_type}" + Style.RESET_ALL)
        
        # Ensure all vehicle IDs are strings for consistent handling
        identifiers = []
        if query_result.identifiers:
            identifiers = [str(id).strip() for id in query_result.identifiers]
            print(Fore.MAGENTA + f"Identifiers: {', '.join(identifiers)}" + Style.RESET_ALL)
        
        # Debug the raw ID formats to help troubleshoot
        if identifiers:
            print(Fore.CYAN + f"Original identifiers: {query_result.identifiers}" + Style.RESET_ALL)
            print(Fore.CYAN + f"Identifier types: {[type(id).__name__ for id in query_result.identifiers]}" + Style.RESET_ALL)
        
        return {
            "samsara_query_type": query_result.query_type,
            "samsara_identifiers": identifiers,
            "samsara_additional_info": query_result.additional_info
        }

    async def fetch_samsara_data(self, state: GraphState) -> GraphState:
        """Fetches data from Samsara API based on query type."""
        print(Fore.YELLOW + "Fetching data from Samsara API...\n" + Style.RESET_ALL)
        
        query_type = state["samsara_query_type"]
        identifiers = state["samsara_identifiers"]
        additional_info = state.get("samsara_additional_info", {})
        samsara_data = ""
        
        try:
            print(Fore.CYAN + f"Query type: {query_type}" + Style.RESET_ALL)
            print(Fore.CYAN + f"Identifiers: {identifiers}" + Style.RESET_ALL)
            print(Fore.CYAN + f"Additional info: {additional_info}" + Style.RESET_ALL)
            
            # Handle standard vehicle location queries
            if query_type == "vehicle_location":
                # Check if we need real-time feed data or standard location data
                if additional_info.get("real_time", False):
                    # Use the new location feed endpoint for real-time data
                    print(Fore.CYAN + "Using real-time location feed endpoint" + Style.RESET_ALL)
                    location_data = await self.samsara_tools.get_vehicle_locations_feed(
                        identifiers if identifiers else None
                    )
                    # Format the data for email
                    samsara_data = self.samsara_tools.format_location_feed_for_email(location_data)
                else:
                    # Use standard location endpoint
                    print(Fore.CYAN + "Using standard location endpoint" + Style.RESET_ALL)
                    location_data = await self.samsara_tools.get_vehicle_locations(
                        identifiers if identifiers else None
                    )
                    # Format the data for email
                    samsara_data = self.samsara_tools.format_location_for_email(location_data)
            
            # Handle standard vehicle info queries        
            elif query_type == "vehicle_info":
                if identifiers and len(identifiers) > 0:
                    # Get specific vehicle information
                    print(Fore.CYAN + f"Getting vehicle info for: {identifiers[0]}" + Style.RESET_ALL)
                    # Use the same API endpoint but format differently
                    vehicle_data = await self.samsara_tools.get_vehicle_locations(
                        identifiers if identifiers else None
                    )
                    
                    # Also get driver assignments for these vehicles to include driver information
                    driver_assignments = await self.samsara_tools.get_vehicle_driver_assignments(identifiers)
                    
                    # Format with both vehicle and driver information
                    samsara_data = self.samsara_tools.format_vehicle_info_for_email(
                        vehicle_data, 
                        driver_assignments
                    )
                else:
                    # Get all vehicles
                    vehicles = await self.samsara_tools.get_all_vehicles()
                    
                    # Get all vehicle IDs to fetch driver assignments
                    vehicle_ids = [str(vehicle.get("id")) for vehicle in vehicles if vehicle.get("id")]
                    
                    # Get driver assignments for all vehicles
                    driver_assignments = await self.samsara_tools.get_vehicle_driver_assignments(vehicle_ids)
                    
                    # Format with both vehicle and driver information
                    samsara_data = self.samsara_tools.format_vehicle_info_for_email(
                        {"data": vehicles}, 
                        driver_assignments
                    )
                    
            # Handle standard driver info queries
            elif query_type == "driver_info":
                if identifiers and len(identifiers) > 0:
                    try:
                        # First try directly with the ID as a driver ID
                        driver_info = await self.samsara_tools.get_driver_info(identifiers[0])
                        
                        # If we get a 404 or empty response, the ID might be a vehicle ID
                        if not driver_info or "error" in driver_info:
                            print(Fore.YELLOW + f"Driver not found, trying to get driver assignment for vehicle: {identifiers[0]}" + Style.RESET_ALL)
                            
                            # Get driver assignment for the vehicle
                            driver_assignments = await self.samsara_tools.get_vehicle_driver_assignments([identifiers[0]])
                            
                            # Extract driver ID from assignment
                            if driver_assignments and "data" in driver_assignments and driver_assignments["data"]:
                                vehicle_data = driver_assignments["data"][0]
                                if "driverAssignments" in vehicle_data and vehicle_data["driverAssignments"]:
                                    # Get the first driver assignment (most recent)
                                    assignment = vehicle_data["driverAssignments"][0]
                                    if "driver" in assignment and assignment["driver"]:
                                        driver_id = assignment["driver"].get("id")
                                        driver_name = assignment["driver"].get("name", "Unknown")
                                        vehicle_name = vehicle_data.get("name", "Unknown Vehicle")
                                        
                                        if driver_id:
                                            print(Fore.GREEN + f"Found driver {driver_name} (ID: {driver_id}) for vehicle {identifiers[0]}" + Style.RESET_ALL)
                                            # Now get the driver info with the correct ID
                                            driver_info = await self.samsara_tools.get_driver_info(driver_id)
                                            print(f"Driver info response: {driver_info}")
                                            
                                            # Format the driver information
                                            if isinstance(driver_info, dict) and not "error" in driver_info:
                                                formatted_driver = "Driver Information:\n\n"
                                                
                                                # Check if the response has a data field
                                                if "data" in driver_info:
                                                    driver_data = driver_info["data"]
                                                    formatted_driver += f"- ID: {driver_data.get('id', 'Not available')}\n"
                                                    formatted_driver += f"- Name: {driver_data.get('name', 'Not available')}\n"
                                                    
                                                    # Add other fields if available
                                                    if "username" in driver_data:
                                                        formatted_driver += f"- Username: {driver_data['username']}\n"
                                                    if "phone" in driver_data:
                                                        formatted_driver += f"- Phone: {driver_data['phone']}\n"
                                                    if "licenseNumber" in driver_data:
                                                        formatted_driver += f"- License: {driver_data['licenseNumber']}\n"
                                                else:
                                                    # Direct fields
                                                    formatted_driver += f"- ID: {driver_info.get('id', 'Not available')}\n"
                                                    formatted_driver += f"- Name: {driver_info.get('name', 'Not available')}\n"
                                                
                                                # Add vehicle assignment info
                                                formatted_driver += "\nVehicle Assignment:\n"
                                                formatted_driver += f"- Vehicle: {vehicle_name} (ID: {vehicle_data.get('id')})\n"
                                                formatted_driver += f"- Assigned since: {assignment.get('startTime', 'Unknown')}\n"
                                                
                                                samsara_data = formatted_driver
                                            else:
                                                samsara_data = f"Driver Information:\n{driver_info}"
                        else:
                            # Process direct driver info response
                            if isinstance(driver_info, dict) and "data" in driver_info:
                                driver_data = driver_info["data"]
                                formatted_driver = "Driver Information:\n\n"
                                formatted_driver += f"- ID: {driver_data.get('id', 'Not available')}\n"
                                formatted_driver += f"- Name: {driver_data.get('name', 'Not available')}\n"
                                
                                # Add other fields if available
                                if "username" in driver_data:
                                    formatted_driver += f"- Username: {driver_data['username']}\n"
                                if "phone" in driver_data:
                                    formatted_driver += f"- Phone: {driver_data['phone']}\n"
                                if "licenseNumber" in driver_data:
                                    formatted_driver += f"- License: {driver_data['licenseNumber']}\n"
                                
                                samsara_data = formatted_driver
                            else:
                                samsara_data = f"Driver Information:\n{driver_info}"
                    except Exception as e:
                        print(Fore.RED + f"Error getting driver info: {str(e)}" + Style.RESET_ALL)
                        import traceback
                        traceback.print_exc()  # Print full stack trace for debugging
                        samsara_data = "Error: Unable to retrieve driver information at this time."
                else:
                    drivers = await self.samsara_tools.get_all_drivers()
                    samsara_data = f"All Driver Information:\n{drivers}"
            
            # Handle driver assignments query
            elif query_type == "driver_assignments":
                driver_assignments = await self.samsara_tools.get_vehicle_driver_assignments(
                    identifiers if identifiers else None
                )
                samsara_data = self.samsara_tools.format_driver_assignments_for_email(driver_assignments)
            
            # Handle immobilizer status query
            elif query_type == "immobilizer_status":
                # Get start time from additional info if available
                start_time = additional_info.get("start_time")
                
                immobilizer_data = await self.samsara_tools.get_vehicle_immobilizer_stream(
                    identifiers if identifiers else None,
                    start_time
                )
                samsara_data = self.samsara_tools.format_immobilizer_data_for_email(immobilizer_data)
            
            # Handle location history query
            elif query_type == "location_history":
                # Get time range from additional info
                start_time = additional_info.get("start_time")
                end_time = additional_info.get("end_time")
                
                if not start_time or not end_time:
                    # Default to last 24 hours if not specified
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    end_time = now.isoformat() + "Z"
                    start_time = (now - timedelta(hours=24)).isoformat() + "Z"
                
                location_history = await self.samsara_tools.get_location_history(
                    identifiers if identifiers else None,
                    start_time,
                    end_time
                )
                samsara_data = self.samsara_tools.format_location_history_for_email(location_history)
            
            # Handle vehicle stats query
            elif query_type == "vehicle_stats":
                # Get stat types from additional info if available
                stat_types = additional_info.get("types", ["spreaderGranularName", "evChargingCurrentMilliAmp"])
                
                vehicle_stats = await self.samsara_tools.get_vehicle_stats_feed(
                    identifiers if identifiers else None,
                    stat_types
                )
                samsara_data = self.samsara_tools.format_vehicle_stats_for_email(vehicle_stats)
            
            # Handle vehicle stats history query
            elif query_type == "vehicle_stats_history":
                # Get time range and stat types from additional info
                start_time = additional_info.get("start_time")
                end_time = additional_info.get("end_time")
                stat_types = additional_info.get("types", ["spreaderGranularName", "evChargingCurrentMilliAmp"])
                
                if not start_time or not end_time:
                    # Default to last 24 hours if not specified
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    end_time = now.isoformat() + "Z"
                    start_time = (now - timedelta(hours=24)).isoformat() + "Z"
                
                stats_history = await self.samsara_tools.get_vehicle_stats_history(
                    identifiers if identifiers else None,
                    start_time,
                    end_time,
                    stat_types
                )
                samsara_data = self.samsara_tools.format_vehicle_stats_for_email(stats_history)
            
            # Handle tachograph files query
            elif query_type == "tachograph_files":
                # Get start time and after token from additional info
                start_time = additional_info.get("start_time")
                after = additional_info.get("after")
                
                if not start_time:
                    # Default to last 7 days if not specified
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    start_time = (now - timedelta(days=7)).isoformat() + "Z"
                
                tachograph_data = await self.samsara_tools.get_tachograph_files_history(
                    identifiers if identifiers else None,
                    start_time,
                    after
                )
                samsara_data = self.samsara_tools.format_tachograph_files_for_email(tachograph_data)
        
        except Exception as e:
            print(Fore.RED + f"Error fetching Samsara data: {str(e)}" + Style.RESET_ALL)
            import traceback
            traceback.print_exc()  # Add traceback for more detailed error information
            samsara_data = "Error: Unable to retrieve data from Samsara at this time."
        
        # Final output to see what we're sending to the email generator (truncated for large outputs)
        print(Fore.GREEN + "Formatted Samsara data for email:" + Style.RESET_ALL)
        if len(samsara_data) > 500:
            print(samsara_data[:500] + "...")
        else:
            print(samsara_data)
        
        return {"retrieved_samsara_data": samsara_data}

    def generate_samsara_response(self, state: GraphState) -> GraphState:
        """Generates a response using the Samsara data."""
        print(Fore.YELLOW + "Generating response with Samsara data...\n" + Style.RESET_ALL)
        
        original_query = state["current_email"].body
        query_type = state["samsara_query_type"]
        samsara_data = state["retrieved_samsara_data"]
        
        # Check if there's actually data in the response
        no_data_indicators = [
            "No vehicle location data available",
            "No vehicle information available",
            "No driver information available",
            "Error: Unable to retrieve data",
            "API Error:"
        ]
        
        has_data = True
        for indicator in no_data_indicators:
            if indicator in samsara_data:
                has_data = False
                break
        
        # In case of vehicle location, specifically check for the format of location data
        if query_type == "vehicle_location" and "Vehicle Locations:" in samsara_data:
            # If it just says "no data available" after the header
            has_data = not "No location data available" in samsara_data
        
        # For vehicle info requests, specifically look for vehicle details
        if query_type == "vehicle_info" and "Vehicle Information:" in samsara_data:
            # If all fields say "Not available", consider it as no data
            not_available_count = samsara_data.count("Not available")
            has_data = not_available_count < 5  # If almost everything is "Not available"
        
        # Add a debug print to see what we determined
        print(Fore.CYAN + f"Has valid Samsara data: {has_data}" + Style.RESET_ALL)
        
        # Inject metadata into the samsara_data to help guide the AI
        if has_data:
            additional_info = {
                "query_type": query_type,
                "data_found": True
            }
        else:
            additional_info = {
                "query_type": query_type,
                "data_found": False
            }
        
        # Convert to JSON string to include with the data
        import json
        metadata = json.dumps(additional_info)
        
        # Add metadata as a comment at the top of samsara_data
        enhanced_samsara_data = f"<!-- Metadata: {metadata} -->\n{samsara_data}"
        
        response = self.agents.generate_samsara_response.invoke({
            "original_query": original_query,
            "query_type": query_type,
            "samsara_data": enhanced_samsara_data
        })
        
        return {"generated_email": response}

    async def create_draft_response(self, state: GraphState) -> GraphState:
        """Create draft response in email system"""
        print(Fore.YELLOW + "Creating email draft...\n" + Style.RESET_ALL)
        try:
            await self.email_tools.create_draft_reply(
                state["current_email"],
                state["generated_email"]
            )
            print(Fore.GREEN + "Draft created successfully" + Style.RESET_ALL)
            return {"retrieved_documents": "", "trials": 0, "draft_created": True}  # Add explicit flag
        except Exception as e:
            print(Fore.RED + f"Error creating draft: {str(e)}" + Style.RESET_ALL)
            return {"retrieved_documents": "", "trials": 0, "draft_created": False}  # Explicit failed flag

    async def send_email_response(self, state: GraphState) -> GraphState:
        """Send the email response"""
        print(Fore.YELLOW + "Sending email...\n" + Style.RESET_ALL)
        try:
            await self.email_tools.send_reply(
                state["current_email"],
                state["generated_email"]
            )
            print(Fore.GREEN + "Email sent successfully" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error sending email: {str(e)}" + Style.RESET_ALL)
        return {"retrieved_documents": "", "trials": 0}

    def skip_unrelated_email(self, state: GraphState) -> GraphState:
        """Skip processing for unrelated emails"""
        print(Fore.YELLOW + "Skipping unrelated email...\n" + Style.RESET_ALL)
        state["emails"].pop()
        print(Fore.GREEN + "Email skipped" + Style.RESET_ALL)
        return state
    
    async def cleanup(self):
        """Cleanup all resources"""
        await self.email_tools.cleanup()