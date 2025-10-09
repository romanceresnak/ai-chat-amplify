import React from 'react';
import { useUserRole, UserRole } from '@/hooks/useUserRole';

interface ProtectedComponentProps {
  requiredRole: UserRole;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const ProtectedComponent: React.FC<ProtectedComponentProps> = ({ 
  requiredRole, 
  children, 
  fallback = null 
}) => {
  const { hasPermission, isLoading } = useUserRole();

  if (isLoading) {
    return <div className="animate-pulse">Loading permissions...</div>;
  }

  return hasPermission(requiredRole) ? <>{children}</> : <>{fallback}</>;
};