# graph.py
from langgraph.graph import END, StateGraph
from .state import GraphState
from .nodes import Nodes
from typing import Optional
from config import config_manager

class Workflow:
    def __init__(self, service: str = 'gmail', email: str = None):
        """
        Initialize workflow based on service type and email address
        
        Args:
            service: Email service to use ('gmail' or 'outlook')
            email: Specific email address to use (must match a configured account)
        """
        workflow = StateGraph(GraphState)
        config = config_manager.get_config()
        
        # Get appropriate email based on service and account
        if service == 'gmail':
            # Use the provided email or get the first valid account
            if email:
                account = config_manager.get_gmail_account(email)
                if not account:
                    raise ValueError(f"Gmail account not found: {email}")
                email_address = account.email
            else:
                account = config_manager.get_gmail_account()
                if not account:
                    raise ValueError("No Gmail accounts configured")
                email_address = account.email
        else:
            # Use the provided email or get the first valid account
            if email:
                account = config_manager.get_outlook_account(email)
                if not account:
                    raise ValueError(f"Outlook account not found: {email}")
                email_address = account.email
            else:
                account = config_manager.get_outlook_account()
                if not account:
                    raise ValueError("No Outlook accounts configured")
                email_address = account.email
            
        # Initialize nodes with email address
        nodes = Nodes(email_address)

        # Define all graph nodes
        workflow.add_node("load_inbox_emails", nodes.load_new_emails)
        workflow.add_node("is_email_inbox_empty", nodes.is_email_inbox_empty)
        workflow.add_node("categorize_email", nodes.categorize_email)
        workflow.add_node("construct_rag_queries", nodes.construct_rag_queries)
        workflow.add_node("retrieve_from_rag", nodes.retrieve_from_rag)
        workflow.add_node("identify_samsara_query", nodes.identify_samsara_query)
        workflow.add_node("fetch_samsara_data", nodes.fetch_samsara_data)
        workflow.add_node("generate_samsara_response", nodes.generate_samsara_response)
        workflow.add_node("email_writer", nodes.write_draft_email)
        workflow.add_node("email_proofreader", nodes.verify_generated_email)
        workflow.add_node("send_email", nodes.create_draft_response)
        workflow.add_node("skip_unrelated_email", nodes.skip_unrelated_email)

        # Set entry point
        workflow.set_entry_point("load_inbox_emails")

        # Define edges
        workflow.add_edge("load_inbox_emails", "is_email_inbox_empty")
        workflow.add_conditional_edges(
            "is_email_inbox_empty",
            nodes.check_new_emails,
            {
                "process": "categorize_email",
                "empty": END
            }
        )

        workflow.add_conditional_edges(
            "categorize_email",
            nodes.route_email_based_on_category,
            {
                "product related": "construct_rag_queries",
                "samsara related": "identify_samsara_query",
                "not product related": "email_writer",
                "unrelated": "skip_unrelated_email"
            }
        )

        workflow.add_edge("construct_rag_queries", "retrieve_from_rag")
        workflow.add_edge("retrieve_from_rag", "email_writer")
        workflow.add_edge("identify_samsara_query", "fetch_samsara_data")
        workflow.add_edge("fetch_samsara_data", "generate_samsara_response")
        workflow.add_edge("generate_samsara_response", "email_proofreader")
        workflow.add_edge("email_writer", "email_proofreader")

        workflow.add_conditional_edges(
            "email_proofreader",
            nodes.must_rewrite,
            {
                "send": "send_email",
                "rewrite": "email_writer",
                "process": "categorize_email",  # Added for handling next email
                "empty": END  # Added for handling no more emails
            }
        )

        workflow.add_edge("send_email", "is_email_inbox_empty")
        workflow.add_edge("skip_unrelated_email", "is_email_inbox_empty")

        self.app = workflow.compile()
        self.nodes = nodes  # Store nodes for cleanup