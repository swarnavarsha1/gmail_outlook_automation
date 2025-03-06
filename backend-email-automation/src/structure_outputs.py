from pydantic import BaseModel, Field
from typing import Any, Dict, List
from enum import Enum
from datetime import datetime, timedelta

# **Categorize Email Output**
class EmailCategory(str, Enum):
    product_enquiry = "product_enquiry"
    customer_complaint = "customer_complaint"
    customer_feedback = "customer_feedback"
    samsara_location_query = "samsara_location_query"
    samsara_driver_query = "samsara_driver_query"
    samsara_vehicle_query = "samsara_vehicle_query"
    unrelated = "unrelated"

class CategorizeEmailOutput(BaseModel):
    category: EmailCategory = Field(
        ..., 
        description="The category assigned to the email, indicating its type based on predefined rules."
    )

# **RAG Query Output**
class RAGQueriesOutput(BaseModel):
    queries: List[str] = Field(
        ..., 
        description="A list of up to three questions representing the customer's intent, based on their email."
    )

# **Email Writer Output**
class WriterOutput(BaseModel):
    email: str = Field(
        ..., 
        description="The draft email written in response to the customer's inquiry, adhering to company tone and standards."
    )

# **Proofreader Email Output**
class ProofReaderOutput(BaseModel):
    feedback: str = Field(
        ..., 
        description="Detailed feedback explaining why the email is or is not sendable."
    )
    send: bool = Field(
        ..., 
        description="Indicates whether the email is ready to be sent (true) or requires rewriting (false)."
    )

class SamsaraQueryType(str, Enum):
    # Existing query types
    vehicle_location = "vehicle_location"
    driver_info = "driver_info"
    vehicle_info = "vehicle_info"
    all_vehicles = "all_vehicles"
    all_drivers = "all_drivers"
    
    # New query types
    driver_assignments = "driver_assignments"
    immobilizer_status = "immobilizer_status"
    location_history = "location_history"
    vehicle_stats = "vehicle_stats"
    vehicle_stats_history = "vehicle_stats_history"
    tachograph_files = "tachograph_files"

class SamsaraQueryOutput(BaseModel):
    query_type: SamsaraQueryType = Field(
        ...,
        description="Type of Samsara query identified in the email"
    )
    identifiers: List[str] = Field(
        default_factory=list,
        description="List of identifiers (vehicle IDs, driver IDs, etc.) extracted from the email"
    )
    additional_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any additional parameters for the query"
    )
    
    # Initialize with appropriate values for different query types
    def __init__(self, **data):
        super().__init__(**data)
        
        # Set default parameters based on query type
        if self.query_type == SamsaraQueryType.vehicle_location:
            # Check if we need to set real_time based on input data
            if 'additional_info' in data and 'real_time' not in self.additional_info:
                self.additional_info['real_time'] = data.get('real_time', False)
            elif 'additional_info' not in data or not self.additional_info:
                self.additional_info = {'real_time': False, 'include_address': True}
                
        elif self.query_type == SamsaraQueryType.location_history:
            # Set default time window for location history (last 24 hours)
            if 'additional_info' not in data or not self.additional_info:
                now = datetime.utcnow()
                end_time = now.isoformat() + "Z"
                start_time = (now - timedelta(hours=24)).isoformat() + "Z"
                
                self.additional_info = {
                    'start_time': start_time,
                    'end_time': end_time
                }
                
        elif self.query_type == SamsaraQueryType.vehicle_stats_history:
            # Set default time window for stats history (last 24 hours)
            if 'additional_info' not in data or not self.additional_info:
                now = datetime.utcnow()
                end_time = now.isoformat() + "Z"
                start_time = (now - timedelta(hours=24)).isoformat() + "Z"
                
                self.additional_info = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'types': ['spreaderGranularName', 'evChargingCurrentMilliAmp']
                }
                
        elif self.query_type == SamsaraQueryType.tachograph_files:
            # Set default time window for tachograph files (last 7 days)
            if 'additional_info' not in data or not self.additional_info:
                now = datetime.utcnow()
                start_time = (now - timedelta(days=7)).isoformat() + "Z"
                
                self.additional_info = {
                    'start_time': start_time
                }
                
        elif self.query_type == SamsaraQueryType.vehicle_stats:
            # Set default stats types
            if 'additional_info' not in data or not self.additional_info:
                self.additional_info = {
                    'types': ['spreaderGranularName', 'evChargingCurrentMilliAmp']
                }
                
        elif self.query_type == SamsaraQueryType.immobilizer_status:
            # Set defaults for immobilizer stream
            if 'additional_info' not in data or not self.additional_info:
                now = datetime.utcnow()
                start_time = (now - timedelta(hours=1)).isoformat() + "Z"
                
                self.additional_info = {
                    'start_time': start_time
                }