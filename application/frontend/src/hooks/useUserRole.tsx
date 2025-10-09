import { useEffect, useState } from 'react';
import { Auth } from 'aws-amplify';

export type UserRole = 'Admin' | 'WriteAccess' | 'ReadOnly' | null;

interface UseUserRoleReturn {
  role: UserRole;
  isLoading: boolean;
  hasPermission: (requiredRole: UserRole) => boolean;
  canRead: boolean;
  canWrite: boolean;
  isAdmin: boolean;
}

const roleHierarchy: Record<UserRole, number> = {
  Admin: 3,
  WriteAccess: 2,
  ReadOnly: 1,
  null: 0
};

export const useUserRole = (): UseUserRoleReturn => {
  const [role, setRole] = useState<UserRole>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUserRole = async () => {
      try {
        const user = await Auth.currentAuthenticatedUser();
        const groups = user.signInUserSession?.idToken?.payload?.['cognito:groups'] || [];
        
        if (groups.includes('Admin')) {
          setRole('Admin');
        } else if (groups.includes('WriteAccess')) {
          setRole('WriteAccess');
        } else if (groups.includes('ReadOnly')) {
          setRole('ReadOnly');
        } else {
          setRole('ReadOnly'); // Default to ReadOnly if no group
        }
      } catch (error) {
        console.error('Error fetching user role:', error);
        setRole(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserRole();
  }, []);

  const hasPermission = (requiredRole: UserRole): boolean => {
    if (!role || !requiredRole) return false;
    return roleHierarchy[role] >= roleHierarchy[requiredRole];
  };

  return {
    role,
    isLoading,
    hasPermission,
    canRead: hasPermission('ReadOnly'),
    canWrite: hasPermission('WriteAccess'),
    isAdmin: role === 'Admin'
  };
};