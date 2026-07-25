import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell               from './components/layout/AppShell';
import Landing                from './pages/Landing';
import Login                  from './pages/Login';
import Dashboard              from './pages/Dashboard';
import DeploymentPlanner      from './pages/DeploymentPlanner';
import DeploymentDetail       from './pages/DeploymentDetail';
import IncidentFeed           from './pages/IncidentFeed';
import RootCauseAnalysis      from './pages/RootCauseAnalysis';
import RecoveryApproval       from './pages/RecoveryApproval';
import RecoveryVerification   from './pages/RecoveryVerification';
import KnowledgeBase          from './pages/KnowledgeBase';
import PostmortemReport       from './pages/PostmortemReport';
import Settings               from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes — no shell */}
        <Route path="/"      element={<Landing />} />
        <Route path="/login" element={<Login />} />

        {/* App routes — with shell */}
        <Route element={<AppShell />}>
          <Route path="/dashboard"                    element={<Dashboard />} />
          <Route path="/deployments"                  element={<DeploymentPlanner />} />
          <Route path="/deployments/:id"              element={<DeploymentDetail />} />
          <Route path="/incidents"                    element={<IncidentFeed />} />
          <Route path="/incidents/:id/rca"            element={<RootCauseAnalysis />} />
          <Route path="/incidents/:id/recovery"       element={<RecoveryApproval />} />
          <Route path="/incidents/:id/verify"         element={<RecoveryVerification />} />
          <Route path="/knowledge"                    element={<KnowledgeBase />} />
          <Route path="/postmortem/:id"               element={<PostmortemReport />} />
          <Route path="/settings"                     element={<Settings />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
