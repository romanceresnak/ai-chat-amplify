'use client';

import AuthProvider from '@/components/AuthProvider';
import ChatInterface from '@/components/ChatInterface';
import PresentationSidebar from '@/components/PresentationSidebar';
import UserMenu from '@/components/UserMenu';

export default function Home() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-gray-100">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center h-16">
              <div className="flex-1"></div>
              <h1 className="flex-1 text-center text-xl font-semibold text-gray-800">
                AI Chat Assistant
              </h1>
              <div className="flex-1 flex justify-end">
                <UserMenu />
              </div>
            </div>
          </div>
        </header>
        <main className="flex h-[calc(100vh-4rem)]">
          <PresentationSidebar />
          <div className="flex-1">
            <ChatInterface />
          </div>
        </main>
      </div>
    </AuthProvider>
  );
}