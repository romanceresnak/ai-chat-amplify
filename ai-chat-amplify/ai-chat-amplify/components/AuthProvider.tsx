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
              <p className="text-gray-600">Prihlásenie do aplikácie</p>
            </div>
          );
        },
      }}
      formFields={{
        signUp: {
          email: {
            label: 'Email',
            placeholder: 'Zadajte váš email',
            isRequired: true,
          },
          password: {
            label: 'Heslo',
            placeholder: 'Zadajte heslo (min. 8 znakov)',
            isRequired: true,
          },
        },
        signIn: {
          email: {
            label: 'Email',
            placeholder: 'Zadajte váš email',
          },
          password: {
            label: 'Heslo',
            placeholder: 'Zadajte vaše heslo',
          },
        },
      }}
    >
      {children}
    </Authenticator>
  );
}