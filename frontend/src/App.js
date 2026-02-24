import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import AssistantAdminDashboard from "./pages/AssistantAdminDashboard";
import ParticipantDashboard from "./pages/ParticipantDashboard";
import SupervisorDashboard from "./pages/SupervisorDashboard_new";
import TrainerDashboard from "./pages/TrainerDashboard";
import TrainerChiefFeedback from "./pages/TrainerChiefFeedback";
import TrainerChecklist from "./pages/TrainerChecklist";
import CoordinatorDashboard from "./pages/CoordinatorDashboard";
import CalendarDashboard from "./pages/CalendarDashboard";
import SuperAdminDashboard from "./pages/SuperAdminDashboard";
import SuperAdminPortal from "./pages/SuperAdminPortal";
import FinanceDashboard from "./pages/FinanceDashboard";
import MarketingDashboard from "./pages/MarketingDashboard";
import TakeTest from "./pages/TakeTest";
import TestResults from "./pages/TestResults";
import ResultsSummary from "./pages/ResultsSummary";
import FeedbackForm from "./pages/FeedbackForm";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "./context/ThemeContext";
import PWAInstallPrompt from "./components/PWAInstallPrompt";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Create axios instance with interceptor
export const axiosInstance = axios.create({
  baseURL: API,
});

axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      axiosInstance
        .get("/auth/me")
        .then((res) => {
          setUser(res.data);
        })
        .catch(() => {
          localStorage.removeItem("token");
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem("token", token);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-xl font-semibold text-indigo-600">Loading...</div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
          <Route
            path="/"
            element={
              user ? (
                user.role === "participant" ? (
                  <Navigate to="/participant" replace />
                ) : user.role === "supervisor" || user.role === "pic_supervisor" ? (
                  <Navigate to="/supervisor" replace />
                ) : user.role === "finance" ? (
                  <Navigate to="/finance" replace />
                ) : user.role === "marketing" ? (
                  <Navigate to="/marketing" replace />
                ) : (
                  // All other roles (admin, assistant_admin, coordinator, trainer) and super admin go to calendar
                  <Navigate to="/calendar" replace />
                )
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/login"
            element={
              user ? (
                <Navigate to="/" replace />
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/calendar"
            element={
              user && ["admin", "assistant_admin", "coordinator", "trainer"].includes(user.role) ? (
                <CalendarDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/admin"
            element={
              user && (user.role === "admin" || user.email === "arjuna@mddrc.com.my") ? (
                <AdminDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/super-admin"
            element={
              user && user.email === "arjuna@mddrc.com.my" ? (
                <SuperAdminDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/participant"
            element={
              user && user.role === "participant" ? (
                <ParticipantDashboard user={user} onLogout={handleLogout} onUserUpdate={setUser} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/supervisor"
            element={
              user && (user.role === "supervisor" || user.role === "pic_supervisor") ? (
                <SupervisorDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/trainer"
            element={
              user && user.role === "trainer" ? (
                <TrainerDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/trainer-checklist/:sessionId/:participantId"
            element={
              user && user.role === "trainer" ? (
                <TrainerChecklist user={user} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/trainer-dashboard"
            element={
              user && user.role === "trainer" ? (
                <TrainerDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/coordinator"
            element={
              user && user.role === "coordinator" ? (
                <CoordinatorDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/assistant-admin"
            element={
              user && user.role === "assistant_admin" ? (
                <AssistantAdminDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/take-test/:testId/:sessionId"
            element={
              user && user.role === "participant" ? (
                <TakeTest />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/test-results/:resultId"
            element={
              user && user.role === "participant" ? (
                <TestResults />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/dashboard"
            element={
              user ? (
                user.role === "participant" ? (
                  <Navigate to="/participant" replace />
                ) : user.role === "admin" ? (
                  <Navigate to="/admin" replace />
                ) : (
                  <Navigate to="/" replace />
                )
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/results-summary/:sessionId"
            element={
              user && (user.role === "admin" || user.role === "coordinator" || user.role === "trainer") ? (
                <ResultsSummary />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/feedback/:sessionId"
            element={
              user && user.role === "participant" ? (
                <FeedbackForm user={user} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/finance"
            element={
              user && (user.role === "finance" || user.role === "admin" || user.email === "arjuna@mddrc.com.my") ? (
                <FinanceDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/marketing"
            element={
              user && (user.role === "marketing" || user.role === "admin" || user.role === "super_admin" || (user.additional_roles && user.additional_roles.includes("marketing"))) ? (
                <MarketingDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/superadmin"
            element={
              user && (user.role === "super_admin" || user.email === "arjuna@mddrc.com.my") ? (
                <SuperAdminPortal />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </ThemeProvider>
  );
}

export default App;
