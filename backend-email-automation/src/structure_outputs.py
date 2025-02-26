from pydantic import BaseModel, Field
from typing import Any, Dict, List
from enum import Enum

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
    vehicle_location = "vehicle_location"
    driver_info = "driver_info"
    vehicle_info = "vehicle_info"
    all_vehicles = "all_vehicles"
    all_drivers = "all_drivers"

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