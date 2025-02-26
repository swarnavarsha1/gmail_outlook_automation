import React, { useState, useEffect } from 'react';
import { Mail, Search, Loader2, Inbox } from 'lucide-react';
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SimplifiedTimeframeSelector } from "@/components/ui/simplified-timeframe";
import { useToast } from "@/components/hooks/use-toast";

interface Account {
  email: string;
  service: string;
  isConfigured: boolean;
}

interface EmailSidebarProps {
  onAccountChange: (email: string, service: string) => void;
}

interface SearchResult {
  count: number;
  search_term: string;
  hours_searched: number;
  time_period: string;
}

const EmailSidebar: React.FC<EmailSidebarProps> = ({ onAccountChange }) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [timeValue, setTimeValue] = useState<string>("24");
  const [timeUnit, setTimeUnit] = useState<'hours' | 'days'>('hours');
  const [isCheckingGmail, setIsCheckingGmail] = useState(false);
  const [isCheckingOutlook, setIsCheckingOutlook] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await fetch('/api/accounts');
        if (!response.ok) {
          throw new Error('Failed to fetch accounts');
        }
        const accountsData = await response.json();
        setAccounts(accountsData);
        
        if (accountsData.length > 0 && !selectedAccount) {
          setSelectedAccount(accountsData[0].email);
          onAccountChange(accountsData[0].email, accountsData[0].service);
        }
      } catch (error) {
        setError('Failed to load email accounts');
        console.error('Error fetching accounts:', error);
      }
    };

    fetchAccounts();
  }, []);

  const handleAccountClick = (account: Account) => {
    setSelectedAccount(account.email);
    onAccountChange(account.email, account.service);
    // Clear search when changing accounts
    setSearchTerm('');
    setSearchResult(null);
  };

  const handleTimeframeChange = (value: string, unit: 'hours' | 'days') => {
    setTimeValue(value);
    setTimeUnit(unit);
  };

  const calculateHours = (): number => {
    const numValue = parseInt(timeValue) || 0;
    return timeUnit === 'days' ? numValue * 24 : numValue;
  };

  const performSearch = async () => {
    if (!searchTerm.trim() || !selectedAccount || isSearching) return;
    
    const hours = calculateHours();
    if (hours <= 0) {
      setError('Please enter a valid time period');
      return;
    }

    setIsSearching(true);
    setError(null);
    
    try {
      const selectedAccountData = accounts.find(acc => acc.email === selectedAccount);
      if (!selectedAccountData) return;

      const params = new URLSearchParams({
        service: selectedAccountData.service,
        search_term: searchTerm.trim(),
        hours: hours.toString()
      });

      const response = await fetch(`/api/email-search?${params}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to perform search');
      }

      const data = await response.json();
      setSearchResult(data);
    } catch (error: any) {
      console.error('Search error:', error);
      setError(error.message || 'Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchTerm.trim()) {
      performSearch();
    }
  };

  const checkEmails = async (service: string) => {
    const setLoading = service === 'gmail' ? setIsCheckingGmail : setIsCheckingOutlook;
    
    try {
      setLoading(true);
      const response = await fetch(`/api/check-emails?service=${service}`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to check emails');
      }
      
      const result = await response.json();
      const logMessages = result.logs?.filter(Boolean) || [];

      // Show check completed toast
      toast({
        title: `${service.charAt(0).toUpperCase() + service.slice(1)} Check Complete`,
        description: (
          <div className="mt-2">
            <p className="mb-2">{result.message}</p>
            <div className="text-sm">
              Processed: {result.stats.processed_emails} emails
            </div>
          </div>
        ),
        duration: Infinity, // Make it persistent
      });

      // If drafts were created, show draft generation toast
      if (result.stats.drafts_created > 0) {
        toast({
          title: "Drafts Generated",
          description: (
            <div className="mt-2">
              <div className="mb-2">
                Created {result.stats.drafts_created} draft{result.stats.drafts_created > 1 ? 's' : ''}
              </div>
              <div className="max-h-[300px] overflow-y-auto border-t pt-2">
                {logMessages.map((log: string, index: number) => (
                  <div 
                    key={index}
                    className="text-xs font-mono py-0.5"
                  >
                    {log}
                  </div>
                ))}
              </div>
            </div>
          ),
          duration: Infinity, // Make it persistent
        });
      }
      
    } catch (error: any) {
      console.error('Error checking emails:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || 'Failed to check emails',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-72 bg-white h-screen border-r border-gray-200">
      <div className="flex items-center space-x-2 px-4 h-16 border-b border-gray-200">
        <Mail className="h-6 w-6 text-indigo-600" />
        <span className="text-xl font-semibold text-gray-900">EmailMonitor</span>
      </div>
      
      <div className="p-4">
        {/* Email Accounts Section */}
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          EMAIL ACCOUNTS
        </h2>

        <div className="space-y-2 mb-6">
          {accounts.map((account) => {
            const isSelected = selectedAccount === account.email;
            return (
              <div
                key={account.email}
                onClick={() => handleAccountClick(account)}
                className={cn(
                  "flex items-start space-x-3 p-2 rounded-md cursor-pointer transition-colors",
                  isSelected ? "bg-blue-50 text-blue-600" : "hover:bg-gray-50"
                )}
              >
                <div className="mt-0.5">
                  <Mail className={cn(
                    "h-4 w-4",
                    isSelected ? "text-blue-500" : "text-gray-400"
                  )} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium truncate">
                    {account.email}
                  </span>
                  <span className="text-xs text-gray-500 capitalize">
                    {account.service}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Search Section */}
        <div className="pt-4 border-t border-gray-200 space-y-3">
          <div className="flex space-x-2">
            <Input
              type="text"
              placeholder="Search by sender..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={handleSearchKeyPress}
              disabled={isSearching}
              className="flex-1"
            />
            <Button
              size="sm"
              onClick={performSearch}
              disabled={!searchTerm.trim() || isSearching}
              variant="outline"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </div>

          <SimplifiedTimeframeSelector
            onTimeframeChange={handleTimeframeChange}
            defaultValue={timeValue}
            defaultUnit={timeUnit}
            isLoading={isSearching}
          />
          
          {error && (
            <div className="text-sm text-red-500">
              {error}
            </div>
          )}
          
          {searchResult && (
            <div className="p-3 bg-gray-50 rounded-md">
              <p className="text-sm">
                Found <span className="font-medium text-indigo-600">
                  {searchResult.count}
                </span> emails from "{searchResult.search_term}"
                <br />
                <span className="text-xs text-gray-500">
                  in the last {searchResult.time_period}
                </span>
              </p>
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-gray-200">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
            CHECK NEW EMAILS
          </h2>
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => checkEmails('gmail')}
              disabled={isCheckingGmail || isCheckingOutlook}
            >
              {isCheckingGmail ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Inbox className="h-4 w-4 mr-2" />
              )}
              Check Gmail
            </Button>
            
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => checkEmails('outlook')}
              disabled={isCheckingGmail || isCheckingOutlook}
            >
              {isCheckingOutlook ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Inbox className="h-4 w-4 mr-2" />
              )}
              Check Outlook
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailSidebar;