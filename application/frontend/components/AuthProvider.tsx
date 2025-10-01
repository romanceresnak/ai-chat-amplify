'use client';

import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { ReactNode } from 'react';

interface AuthProviderProps {
  children: ReactNode;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  return (
    <Authenticator
      loginMechanisms={['email']}
      signUpAttributes={['email']}
      components={{
        Header() {
          return (
            <div className="text-center py-6">
              <h1 className="text-2xl font-bold">AI Chat Assistant</h1>
              <p className="text-gray-600">Sign in to your account</p>
            </div>
          );
        },
      }}
      formFields={{
        signUp: {
          email: {
            label: 'Email',
            placeholder: 'Enter your email',
            isRequired: true,
          },
          password: {
            label: 'Password',
            placeholder: 'Enter password (min. 8 characters)',
            isRequired: true,
          },
        },
        signIn: {
          email: {
            label: 'Email',
            placeholder: 'Enter your email',
          },
          password: {
            label: 'Password',
            placeholder: 'Enter your password',
          },
        },
      }}
    >
      {children}
    </Authenticator>
  );
}