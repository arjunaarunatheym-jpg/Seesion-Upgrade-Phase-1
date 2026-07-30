# Auth Testing Playbook

Focused checks for the current bug:
- POST `/api/auth/login` with the provided super_admin credentials should return a bearer token and user object with `role: super_admin`.
- GET `/api/auth/me` with that bearer token should return the same user.
- Frontend `ProtectedRoute` should allow `/finance` for roles including `super_admin`.
- Finance UI should pass the authenticated `user` object into `InvoicesTab` so role-gated admin controls render without relying on `localStorage.user`.