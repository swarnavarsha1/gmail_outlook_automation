"use client";

import React, { useState } from 'react';
import EmailSidebar from '@/components/email/sidebar';
import EmailDashboard from '@/components/email/dashboard';
import { ToastProvider } from '@/components/ui/toast-context';

interface EmailAccount {
  email: string;
  service: string;
}

const EmailMonitorLayout = () => {
  const [selectedAccount, setSelectedAccount] = useState<EmailAccount | null>(null);

  const handleAccountChange = (email: string, service: string) => {
    setSelectedAccount({ email, service });
  };

  return (
    <ToastProvider>
      <div className="flex h-screen bg-gray-50">
        <EmailSidebar onAccountChange={handleAccountChange} />
        <div className="flex-1 overflow-auto">
          <EmailDashboard selectedAccount={selectedAccount} />
        </div>
      </div>
    </ToastProvider>
  );
};

export default EmailMonitorLayout;