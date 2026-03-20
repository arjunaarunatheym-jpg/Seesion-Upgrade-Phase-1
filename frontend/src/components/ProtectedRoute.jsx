import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ user, allowedRoles, children }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect unauthorized users to their default page
    if (user.role === 'participant') return <Navigate to="/participant" replace />;
    if (user.role === 'supervisor' || user.role === 'pic_supervisor') return <Navigate to="/supervisor" replace />;
    if (user.role === 'trainer') return <Navigate to="/trainer" replace />;
    return <Navigate to="/calendar" replace />;
  }

  return children;
};

export default ProtectedRoute;
