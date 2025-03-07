import asyncio
import io
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import config_manager
from src.graph import Workflow
from src.tools.GmailTools import GmailToolsClass
from src.tools.enhanced_outlook_tools import EnhancedOutlookTools
from datetime import datetime, timedelta
from enum import Enum
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy logs
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('chromadb.telemetry').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.ERROR)

config = config_manager.get_config()

app = FastAPI(
    title="Email Automation",
    version="1.0",
    description="Email Automation API",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class EmailServiceType(Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"

class EmailToolFactory:
    @staticmethod
    def create_email_tool(service_type: EmailServiceType, account_email: Optional[str] = None):
        try:
            if service_type == EmailServiceType.GMAIL:
                if account_email:
                    # Get the specific Gmail account
                    account = config_manager.get_gmail_account(account_email)
                    if not account:
                        raise ValueError(f"Gmail account not found: {account_email}")
                    # Create tool with specific account credentials
                    return GmailToolsClass(account_email)
                else:
                    # Use default account
                    return GmailToolsClass()
            elif service_type == EmailServiceType.OUTLOOK:
                if account_email:
                    # Get the specific Outlook account
                    account = config_manager.get_outlook_account(account_email)
                    if not account:
                        raise ValueError(f"Outlook account not found: {account_email}")
                    # Create tool with specific account credentials
                    return EnhancedOutlookTools(account_email)
                else:
                    # Use default account
                    default_account = config_manager.get_outlook_account()
                    if not default_account:
                        raise ValueError("No Outlook accounts configured")
                    return EnhancedOutlookTools(default_account.email)
        except Exception as e:
            logger.error(f"Error creating email tool: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/email-stats")
async def get_email_stats(
    service: str = Query(..., pattern="^(gmail|outlook)$"),
    hours: int = Query(default=24, ge=1),
    account: Optional[str] = None
):
    """
    Get email statistics for the specified service and time range
    """
    try:
        # Initialize service and tools
        service_type = EmailServiceType(service)
        email_tools = EmailToolFactory.create_email_tool(service_type, account)
        
        # Initialize statistics
        stats = {
            "total": 0,
            "unread": 0,
            "read": 0,
            "replied": 0,
            "drafted": 0
        }
        
        # Fetch emails based on service type
        try:
            if service_type == EmailServiceType.GMAIL:
                # For Gmail
                recent_emails = email_tools.fetch_recent_emails(hours=hours)
                
                # Filter for inbox emails only
                inbox_emails = [
                    email for email in recent_emails 
                    if 'INBOX' in email.get('labelIds', []) and
                    'TRASH' not in email.get('labelIds', []) and
                    'DRAFT' not in email.get('labelIds', [])
                ]
                
                if inbox_emails:
                    # Calculate Gmail stats
                    stats["total"] = len(inbox_emails)
                    stats["unread"] = sum(1 for email in inbox_emails 
                                        if 'UNREAD' in email.get('labelIds', []))
                    
                    # Count replies using threads
                    try:
                        # Get all thread IDs from inbox emails
                        thread_ids = {email.get('threadId') for email in inbox_emails if email.get('threadId')}
                        replied_threads = set()
                        
                        # Get messages from the Sent folder to compare
                        sent_query = f'after:{int((datetime.now() - timedelta(hours=hours)).timestamp())} in:sent'
                        sent_results = email_tools.service.users().messages().list(
                            userId="me",
                            q=sent_query
                        ).execute()
                        sent_messages = sent_results.get("messages", [])
                        
                        # Create a set of thread IDs that have sent messages
                        sent_thread_ids = set()
                        if sent_messages:
                            for msg in sent_messages:
                                msg_detail = email_tools.service.users().messages().get(
                                    userId="me", id=msg['id']).execute()
                                sent_thread_ids.add(msg_detail.get('threadId'))
                        
                        # Check which inbox threads also have sent messages
                        for thread_id in thread_ids:
                            if thread_id in sent_thread_ids:
                                replied_threads.add(thread_id)
                        
                        stats["replied"] = len(replied_threads)
                        if stats['replied'] > 0:
                            logger.debug(f"Found {stats['replied']} replied threads")       
                    except Exception as reply_error:
                        logger.error(f"Error counting Gmail replies: {str(reply_error)}")
                    
                # Fetch Gmail drafts
                try:
                    drafts = email_tools.fetch_draft_replies()
                    stats["drafted"] = len(drafts)
                except Exception as draft_error:
                    logger.error(f"Error fetching Gmail drafts: {str(draft_error)}")
                
            else:
                # For Outlook
                # Fetch inbox messages
                inbox_emails = await email_tools.fetch_recent_emails(
                    hours=hours,
                    folder='inbox'
                )
                
                if inbox_emails:
                    # Calculate Outlook stats
                    stats["total"] = len(inbox_emails)
                    stats["unread"] = sum(1 for email in inbox_emails 
                                        if not email.get('isRead', True))
                    
                    # Get reply count using dedicated method
                    try:
                        stats["replied"] = await email_tools.get_reply_count(hours=hours)
                    except Exception as reply_error:
                        logger.error(f"Error getting Outlook reply count: {str(reply_error)}")
                
                # Fetch Outlook drafts
                    try:
                        drafts = await email_tools.fetch_draft_replies()
                        # Only count valid drafts that have content and are replies
                        stats["drafted"] = len([
                            draft for draft in drafts 
                            if draft.get('subject', '').lower().startswith('re:')
                        ])
                    except Exception as draft_error:
                        logger.error(f"Error fetching Outlook drafts: {str(draft_error)}")
                        stats["drafted"] = 0
                
            # Calculate read count based on total and unread
            stats["read"] = stats["total"] - stats["unread"]
            
        except Exception as fetch_error:
            logger.error(f"Error fetching emails: {str(fetch_error)}")
            # Stats will remain at their default values (all 0)
        
        # Time range warning for large queries
        if hours > 720:  # More than 30 days
            logger.warning(f"Large time range requested: {hours} hours")
        
        return stats
        
    except Exception as e:
        error_msg = f"Error processing email statistics: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
@app.get("/api/accounts")
async def get_accounts():
    """Get configured email accounts"""
    try:
        accounts = config_manager.get_all_accounts()
        return accounts
    except Exception as e:
        logger.error(f"Error getting accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/recent-emails")
async def get_recent_emails(
    service: str = Query(..., pattern="^(gmail|outlook)$"),
    hours: int = Query(default=24, ge=1),
    account: Optional[str] = None
):
    """
    Get recent emails for the specified service and time range
    """
    try:
        # Initialize service and tools
        service_type = EmailServiceType(service)
        email_tools = EmailToolFactory.create_email_tool(service_type, account)
        
        recent_emails = []
        
        try:
            if service_type == EmailServiceType.GMAIL:
                # For Gmail
                emails = email_tools.fetch_recent_emails(hours=hours)
                for email in emails:
                    if 'INBOX' in email.get('labelIds', []):
                        headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
                        recent_emails.append({
                            "id": email['id'],
                            "subject": headers.get('subject', 'No Subject'),
                            "sender": headers.get('from', 'Unknown'),
                            "timestamp": email.get('internalDate'),
                            "isRead": 'UNREAD' not in email.get('labelIds', []),
                            "isStarred": 'STARRED' in email.get('labelIds', [])
                        })
            else:
                # For Outlook
                emails = await email_tools.fetch_recent_emails(hours=hours)
                for email in emails:
                    sender_info = email.get('from', {}).get('emailAddress', {})
                    recent_emails.append({
                        "id": email.get('id', ''),
                        "subject": email.get('subject', 'No Subject'),
                        "sender": f"{sender_info.get('name', '')} <{sender_info.get('address', 'Unknown')}>",
                        "timestamp": email.get('receivedDateTime', ''),
                        "isRead": email.get('isRead', False),
                        "isStarred": email.get('flag', {}).get('flagStatus', '') == 'flagged'
                    })
                    
            # Sort emails by timestamp
            recent_emails.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Limit to most recent 10 emails
            recent_emails = recent_emails[:10]
            
            # Format timestamps for consistent display
            for email in recent_emails:
                try:
                    if service_type == EmailServiceType.GMAIL:
                        # Convert Gmail's timestamp (milliseconds since epoch)
                        ts = int(email['timestamp']) / 1000
                        dt = datetime.fromtimestamp(ts)
                    else:
                        # Parse Outlook's ISO timestamp
                        dt = datetime.fromisoformat(email['timestamp'].replace('Z', '+00:00'))
                    
                    # Calculate relative time
                    now = datetime.now(dt.tzinfo)
                    diff = now - dt
                    
                    if diff.days > 0:
                        email['timestamp'] = f"{diff.days}d ago"
                    elif diff.seconds >= 3600:
                        hours = diff.seconds // 3600
                        email['timestamp'] = f"{hours}h ago"
                    else:
                        minutes = diff.seconds // 60
                        email['timestamp'] = f"{minutes}m ago"
                except Exception as e:
                    logger.error(f"Error formatting timestamp: {str(e)}")
                    email['timestamp'] = 'Unknown'
            
            return recent_emails
            
        except Exception as fetch_error:
            logger.error(f"Error fetching recent emails: {str(fetch_error)}")
            return []
        
    except Exception as e:
        error_msg = f"Error processing recent emails: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    try:
        validation_result = config_manager.validate_config()
        
        # Get configured accounts
        accounts = config_manager.get_all_accounts()
        
        # Group accounts by service
        gmail_accounts = [acc for acc in accounts if acc['service'] == 'gmail']
        outlook_accounts = [acc for acc in accounts if acc['service'] == 'outlook']
        
        return {
            "status": "healthy",
            "accounts": {
                "gmail": gmail_accounts,
                "outlook": outlook_accounts
            },
            "configuration": {
                "gmail_configured": validation_result['gmail_configured'],
                "outlook_configured": validation_result['outlook_configured'],
                "ai_configured": validation_result['ai_configured'],
                "samsara_configured": validation_result['samsara_configured']
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/email-search")
async def search_emails(
    service: str = Query(..., pattern="^(gmail|outlook)$"),
    search_term: str = Query(..., min_length=1),
    hours: int = Query(default=24, ge=1),
    account: Optional[str] = None
):
    """
    Search emails for specific sender/customer
    """
    try:
        service_type = EmailServiceType(service)
        email_tools = EmailToolFactory.create_email_tool(service_type, account)
        
        try:
            total_count = 0
            if service_type == EmailServiceType.GMAIL:
                # For Gmail
                emails = email_tools.fetch_recent_emails(hours=hours)
                for email in emails:
                    if 'INBOX' in email.get('labelIds', []):
                        headers = {h['name'].lower(): h['value'] for h in email.get('payload', {}).get('headers', [])}
                        from_header = headers.get('from', '').lower()
                        if search_term.lower() in from_header:
                            total_count += 1
            else:
                # For Outlook
                emails = await email_tools.fetch_recent_emails(hours=hours)
                for email in emails:
                    sender_info = email.get('from', {}).get('emailAddress', {})
                    sender_name = sender_info.get('name', '').lower()
                    sender_email = sender_info.get('address', '').lower()
                    if (search_term.lower() in sender_name or 
                        search_term.lower() in sender_email):
                        total_count += 1
            
            # Format the time period for response
            time_period = (
                f"{hours} hours" if hours < 24 
                else f"{hours // 24} days"
            )
            
            return {
                "count": total_count,
                "search_term": search_term,
                "hours_searched": hours,
                "time_period": time_period
            }
            
        except Exception as fetch_error:
            logger.error(f"Error searching emails: {str(fetch_error)}")
            raise HTTPException(status_code=500, detail=str(fetch_error))
        
    except Exception as e:
        error_msg = f"Error processing email search: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    

@app.post("/api/check-emails")
async def check_emails(
    service: str = Query(..., pattern="^(gmail|outlook)$"),
    account: Optional[str] = None
):
    """
    Trigger email check and draft generation for specified service and account
    """
    try:
        # Create a custom Tee-like stdout that both captures and prints
        import sys
        from io import StringIO
        
        class TeeOutput:
            def __init__(self, original_stdout, capture_buffer):
                self.original_stdout = original_stdout
                self.capture_buffer = capture_buffer
                
            def write(self, message):
                # Write to original stdout (terminal)
                self.original_stdout.write(message)
                # Also capture to our buffer
                self.capture_buffer.write(message)
                
            def flush(self):
                self.original_stdout.flush()
                
        # Set up our capture mechanism
        captured_output = StringIO()
        original_stdout = sys.stdout
        tee_output = TeeOutput(original_stdout, captured_output)
        sys.stdout = tee_output
        
        # Initialize workflow with specific account
        workflow = Workflow(service, account)
        
        initial_state = {
            "emails": [],
            "current_email": None,
            "email_category": "",
            "generated_email": "",
            "rag_queries": [],
            "retrieved_documents": "",
            "writer_messages": [],
            "sendable": False,
            "trials": 0,
            "samsara_query_type": "",
            "samsara_identifiers": [],
            "samsara_additional_info": {},
            "retrieved_samsara_data": ""
        }
        
        processed_count = 0
        drafts_created = 0
        
        try:
            # Execute the workflow
            async for state in workflow.app.astream(initial_state):
                # Let the workflow run and print its messages
                pass
            
            await workflow.nodes.cleanup()
            
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
        
        # Get the captured output
        output_text = captured_output.getvalue()
        
        # Parse the output to count processed emails and drafts
        import re
        email_match = re.search(r'Found (\d+) new emails to process', output_text)
        if email_match:
            processed_count = int(email_match.group(1))
        
        # Count draft creations
        drafts_created = output_text.count("Draft created successfully")
        
        # Log the final statistics
        logger.info(f"Email processing complete - Processed: {processed_count}, Drafts created: {drafts_created}")
        
        # Split the output into lines for the logs response
        output_lines = output_text.splitlines()
        
        return {
            "status": "success",
            "message": f"Email check completed for {service}" + (f" ({account})" if account else ""),
            "stats": {
                "processed_emails": processed_count,
                "drafts_created": drafts_created
            },
            "logs": output_lines
        }
        
    except Exception as e:
        # Make sure to restore stdout in case of exceptions
        if 'original_stdout' in locals():
            sys.stdout = original_stdout
        logger.error(f"Error checking emails: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error checking emails: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)