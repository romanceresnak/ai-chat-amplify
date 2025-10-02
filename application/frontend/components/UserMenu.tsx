'use client';

import { useAuthenticator } from '@aws-amplify/ui-react';
import { LogOut, User } from 'lucide-react';

export default function UserMenu() {
  const { user, signOut } = useAuthenticator((context) => [context.user]);

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        <User className="w-4 h-4 text-gray-600" />
        <span className="text-sm text-gray-700">{user?.signInDetails?.loginId}</span>
      </div>
      <button
        onClick={signOut}
        className="flex items-center gap-1 px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
      >
        <LogOut className="w-3 h-3" />
        Odhlásiť sa
      </button>
    </div>
  );
}