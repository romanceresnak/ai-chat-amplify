'use client';

import { useAuthenticator } from '@aws-amplify/ui-react';
import { LogOut, User } from 'lucide-react';

export default function UserMenu() {
  const { user, signOut } = useAuthenticator((context) => [context.user]);

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <User className="w-5 h-5 text-gray-600" />
        <span className="text-sm text-gray-700">{user?.signInDetails?.loginId}</span>
      </div>
      <button
        onClick={signOut}
        className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Odhlásiť sa
      </button>
    </div>
  );
}