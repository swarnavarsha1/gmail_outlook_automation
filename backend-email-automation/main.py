# main.py
import asyncio
from colorama import Fore, Style
from src.graph import Workflow
import traceback
from config import config_manager
import argparse

# Get configuration
config = config_manager.get_config()

# Config for workflow
workflow_config = {'recursion_limit': 100}

# Validate configuration
validation_result = config_manager.validate_config()

# Check required configurations
if not validation_result['gmail_configured']:
    print(Fore.YELLOW + "Warning: Gmail is not properly configured" + Style.RESET_ALL)
if not validation_result['outlook_configured']:
    print(Fore.YELLOW + "Warning: Outlook is not properly configured" + Style.RESET_ALL)
if not validation_result['ai_configured']:
    print(Fore.YELLOW + "Warning: AI services are not properly configured" + Style.RESET_ALL)

async def run_workflow(service: str = 'gmail', email: str = None):
    """Run workflow for specified email service and account"""
    try:
        # Select appropriate email based on service and account
        if service == 'gmail':
            account = config_manager.get_gmail_account(email)
            if not account:
                raise ValueError(f"Gmail account not found: {email}")
            email_address = account.email
            print(Fore.YELLOW + f"Using Gmail: {email_address}" + Style.RESET_ALL)
        else:
            account = config_manager.get_outlook_account(email)
            if not account:
                raise ValueError(f"Outlook account not found: {email}")
            email_address = account.email
            print(Fore.YELLOW + f"Using Outlook: {email_address}" + Style.RESET_ALL)

        # Initialize workflow
        workflow = Workflow(service, email_address)
        app = workflow.app

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

        print(Fore.GREEN + f"Starting {service} workflow for {email_address}..." + Style.RESET_ALL)
        async for output in app.astream(initial_state, workflow_config):
            for key, value in output.items():
                print(Fore.CYAN + f"Finished running: {key}" + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"Error in {service} workflow: {str(e)}" + Style.RESET_ALL)
        print(Fore.RED + "Traceback:" + Style.RESET_ALL)
        traceback.print_exc()
        raise e
    finally:
        if 'workflow' in locals() and hasattr(workflow, 'nodes'):
            await workflow.nodes.cleanup()

async def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', choices=['gmail', 'outlook'], default='gmail',
                       help='Email service to use')
    parser.add_argument('--email', type=str, help='Email address to use (must match configured account)')
    args = parser.parse_args()
    
    await run_workflow(args.service, args.email)

if __name__ == "__main__":
    asyncio.run(main())