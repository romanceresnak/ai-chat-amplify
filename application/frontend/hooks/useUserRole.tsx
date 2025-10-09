import { useEffect, useState } from 'react';
import { getCurrentUser } from 'aws-amplify/auth';

export type UserRole = 'Admin' | 'WriteAccess' | 'ReadOnly' | null;

interface UseUserRoleReturn {
  role: UserRole;
  isLoading: boolean;
  hasPermission: (requiredRole: UserRole) => boolean;
  canRead: boolean;
  canWrite: boolean;
  isAdmin: boolean;
}

const roleHierarchy: Record<NonNullable<UserRole>, number> = {
  Admin: 3,
  WriteAccess: 2,
  ReadOnly: 1
};

export const useUserRole = (): UseUserRoleReturn => {
  const [role, setRole] = useState<UserRole>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUserRole = async () => {
      try {
        const user = await getCurrentUser();
        // Note: In newer Amplify versions, groups might be accessed differently
        // For now, we'll set a default role and log the user structure
        console.log('Current user:', user);
        
        // TODO: Update this when we have proper Cognito groups integration
        setRole('ReadOnly'); // Default to ReadOnly for now
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
    const userLevel = roleHierarchy[role as NonNullable<UserRole>] || 0;
    const requiredLevel = roleHierarchy[requiredRole as NonNullable<UserRole>] || 0;
    return userLevel >= requiredLevel;
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