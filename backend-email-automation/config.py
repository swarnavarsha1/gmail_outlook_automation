from typing import Dict, Any, List
import os
import json
from dataclasses import dataclass, field

@dataclass
class OutlookAccount:
    client_id: str
    client_secret: str
    tenant_id: str
    email: str

@dataclass
class GmailAccount:
    email: str
    credentials_file: str
    user_email: str

@dataclass
class AIConfig:
    gemini_api_key: str

@dataclass
class SamsaraConfig:
    api_token: str
    base_url: str

@dataclass
class Config:
    outlook_accounts: List[OutlookAccount] = field(default_factory=list)
    gmail_accounts: List[GmailAccount] = field(default_factory=list)
    ai: AIConfig = None
    samsara: SamsaraConfig = None
    environment: str = "development"
    # For backward compatibility
    @property
    def outlook(self):
        return self.outlook_accounts[0] if self.outlook_accounts else None
    
    @property
    def gmail(self):
        return self.gmail_accounts[0] if self.gmail_accounts else None

class ConfigurationManager:
    """Manages application configuration with support for different environments and multiple accounts"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Config:
        """Load configuration based on environment, prioritizing the config file"""
        env = os.getenv('APP_ENV', 'development')
        
        # Default/placeholder configuration - DO NOT PUT REAL VALUES HERE
        default_config_data = {
            'outlook_accounts': [
                {
                    'client_id': '<OUTLOOK_CLIENT_ID>',
                    'client_secret': '<OUTLOOK_CLIENT_SECRET>',
                    'tenant_id': '<OUTLOOK_TENANT_ID>',
                    'email': '<OUTLOOK_EMAIL>'
                }
            ],
            'gmail_accounts': [
                {
                    'email': '<GMAIL_EMAIL>',
                    'credentials_file': '<CREDENTIALS_FILE_PATH>',
                    'user_email': '<USER_EMAIL>'
                }
            ],
            'ai': {
                'gemini_api_key': '<GEMINI_API_KEY>'
            },
            'samsara': {
                'api_token': '<SAMSARA_API_TOKEN>',
                'base_url': 'https://api.samsara.com'
            },
            'environment': env
        }
        
        # Try to load from config file - THIS WILL CONTAIN YOUR REAL VALUES
        config_file = f'config.{env}.json'
        config_data = default_config_data.copy()
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    
                    # Handle backward compatibility - convert old format to new format
                    if 'outlook' in file_config and 'outlook_accounts' not in file_config:
                        file_config['outlook_accounts'] = [file_config.pop('outlook')]
                    if 'gmail' in file_config and 'gmail_accounts' not in file_config:
                        file_config['gmail_accounts'] = [file_config.pop('gmail')]
                    
                    # Update the config data with file values
                    config_data.update(file_config)
                    print(f"Loaded configuration from {config_file}")
            except Exception as e:
                print(f"Error loading config file {config_file}: {str(e)}")
                print("Using default configuration with environment variables as fallback")
        else:
            print(f"Config file {config_file} not found. Using default configuration with environment variables as fallback")
        
        # Create Outlook accounts
        outlook_accounts = []
        # Load from config file accounts
        for account_data in config_data.get('outlook_accounts', []):
            outlook_account = OutlookAccount(
                client_id=account_data.get('client_id', '<OUTLOOK_CLIENT_ID>'),
                client_secret=account_data.get('client_secret', '<OUTLOOK_CLIENT_SECRET>'),
                tenant_id=account_data.get('tenant_id', '<OUTLOOK_TENANT_ID>'),
                email=account_data.get('email', '<OUTLOOK_EMAIL>')
            )
            outlook_accounts.append(outlook_account)
        
        # Create Gmail accounts
        gmail_accounts = []
        # Load from config file accounts
        for account_data in config_data.get('gmail_accounts', []):
            gmail_account = GmailAccount(
                email=account_data.get('email', '<GMAIL_EMAIL>'),
                credentials_file=account_data.get('credentials_file', '<CREDENTIALS_FILE_PATH>'),
                user_email=account_data.get('user_email', '<USER_EMAIL>')
            )
            gmail_accounts.append(gmail_account)

        # Create AI config
        ai_config = AIConfig(
            gemini_api_key=config_data['ai'].get('gemini_api_key', '<GEMINI_API_KEY>')
        )

        # Create Samsara config
        samsara_config = SamsaraConfig(
            api_token=config_data['samsara'].get('api_token', '<SAMSARA_API_TOKEN>'),
            base_url=config_data['samsara'].get('base_url', 'https://api.samsara.com')
        )
        
        return Config(
            outlook_accounts=outlook_accounts,
            gmail_accounts=gmail_accounts,
            ai=ai_config,
            samsara=samsara_config,
            environment=env
        )
    
    def get_config(self) -> Config:
        """Get the current configuration"""
        return self.config
    
    def get_gmail_account(self, email=None):
        """Get a specific Gmail account by email, or the first one if not specified"""
        if not email:
            return self.config.gmail_accounts[0] if self.config.gmail_accounts else None
        
        for account in self.config.gmail_accounts:
            if account.email == email:
                return account
        
        return None
    
    def get_outlook_account(self, email=None):
        """Get a specific Outlook account by email, or the first one if not specified"""
        if not email:
            return self.config.outlook_accounts[0] if self.config.outlook_accounts else None
        
        for account in self.config.outlook_accounts:
            if account.email == email:
                return account
        
        return None
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate the configuration"""
        outlook_valid = all([
            len(self.config.outlook_accounts) > 0,
            all([
                account.client_id not in ['<OUTLOOK_CLIENT_ID>', ''] and
                account.client_secret not in ['<OUTLOOK_CLIENT_SECRET>', ''] and
                account.tenant_id not in ['<OUTLOOK_TENANT_ID>', ''] and
                account.email not in ['<OUTLOOK_EMAIL>', '']
                for account in self.config.outlook_accounts
            ])
        ]) if self.config.outlook_accounts else False
        
        gmail_valid = all([
            len(self.config.gmail_accounts) > 0,
            all([
                account.email not in ['<GMAIL_EMAIL>', ''] and
                account.credentials_file not in ['<CREDENTIALS_FILE_PATH>', ''] and
                account.user_email not in ['<USER_EMAIL>', '']
                for account in self.config.gmail_accounts
            ])
        ]) if self.config.gmail_accounts else False

        ai_valid = self.config.ai.gemini_api_key not in ['<GEMINI_API_KEY>', ''] if self.config.ai else False
        samsara_valid = self.config.samsara.api_token not in ['<SAMSARA_API_TOKEN>', ''] if self.config.samsara else False
        
        return {
            'outlook_configured': outlook_valid,
            'gmail_configured': gmail_valid,
            'ai_configured': ai_valid,
            'samsara_configured': samsara_valid
        }
    
    def get_all_accounts(self):
        """Get all configured email accounts"""
        accounts = []
        
        # Add Gmail accounts
        for account in self.config.gmail_accounts:
            accounts.append({
                'email': account.email,
                'service': 'gmail',
                'isConfigured': bool(account.credentials_file) and account.email not in ['<GMAIL_EMAIL>', ''],
                'user_email': account.user_email
            })
            
        # Add Outlook accounts
        for account in self.config.outlook_accounts:
            accounts.append({
                'email': account.email,
                'service': 'outlook',
                'isConfigured': bool(account.client_id and account.client_secret and account.tenant_id) and 
                                account.email not in ['<OUTLOOK_EMAIL>', '']
            })
            
        return accounts

# Create a singleton instance
config_manager = ConfigurationManager()