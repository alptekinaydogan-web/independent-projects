import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import OwnerOnly from "@/components/OwnerOnly";
import AppShell from "@/components/AppShell";
import { Toaster } from "sonner";

import Login from "@/pages/Login";
import AdminDashboard from "@/pages/admin/Dashboard";
import Representatives from "@/pages/admin/Representatives";
import RepresentativeProfile from "@/pages/admin/RepresentativeProfile";
import ApplicationsReview from "@/pages/admin/ApplicationsReview";
import TVProjects from "@/pages/admin/TVProjects";
import TVProjectEdit from "@/pages/admin/TVProjectEdit";
import AdminProjectView from "@/pages/admin/AdminProjectView";
import Proposals from "@/pages/admin/Proposals";
import AdminReports from "@/pages/admin/Reports";
import AuditLog from "@/pages/admin/AuditLog";
import Admins from "@/pages/admin/Admins";
import Notifications from "@/pages/Notifications";

import RepDashboard from "@/pages/rep/Dashboard";
import TVCatalog from "@/pages/rep/TVCatalog";
import TVProjectDetail from "@/pages/rep/TVProjectDetail";
import SubmitProposal from "@/pages/rep/SubmitProposal";
import ProjectDraft from "@/pages/rep/ProjectDraft";
import RepReports from "@/pages/rep/Reports";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
          <Routes>
            <Route path="/" element={<Login />} />

            <Route element={<ProtectedRoute role="admin"><AppShell role="admin" /></ProtectedRoute>}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/representatives" element={<Representatives />} />
              <Route path="/admin/representatives/:id" element={<RepresentativeProfile />} />
              <Route path="/admin/proposals-review" element={<ApplicationsReview />} />
              <Route path="/admin/tv-projects" element={<TVProjects />} />
              <Route path="/admin/tv-projects/new" element={<TVProjectEdit />} />
              <Route path="/admin/tv-projects/:id" element={<AdminProjectView />} />
              <Route path="/admin/tv-projects/:id/edit" element={<TVProjectEdit />} />
              <Route path="/admin/proposals" element={<Proposals />} />
              <Route path="/admin/reports" element={<AdminReports />} />
              <Route path="/admin/audit-log" element={<AuditLog />} />
              <Route path="/admin/notifications" element={<Notifications />} />
              <Route path="/admin/admins" element={<OwnerOnly><Admins /></OwnerOnly>} />
            </Route>

            <Route element={<ProtectedRoute role="representative"><AppShell role="representative" /></ProtectedRoute>}>
              <Route path="/rep" element={<RepDashboard />} />
              <Route path="/rep/tv" element={<TVCatalog />} />
              <Route path="/rep/tv/:id" element={<TVProjectDetail />} />
              <Route path="/rep/proposals" element={<SubmitProposal />} />
              <Route path="/rep/projects/new" element={<ProjectDraft />} />
              <Route path="/rep/projects/:id" element={<ProjectDraft />} />
              <Route path="/rep/proposals/new" element={<ProjectDraft />} />
              <Route path="/rep/notifications" element={<Notifications />} />
              <Route path="/rep/reports" element={<RepReports />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
