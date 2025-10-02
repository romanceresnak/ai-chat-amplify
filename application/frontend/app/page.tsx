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
            <div className="relative flex justify-end items-center h-16">
              <h1 className="absolute left-1/2 transform -translate-x-1/2 text-xl font-semibold text-gray-800">
                AI Chat Assistant
              </h1>
              <UserMenu />
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