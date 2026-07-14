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
import BannerInventory from "@/pages/InventoryCatalog";
import ProposalsReview from "@/pages/admin/ProposalsReview";
import TVProjects from "@/pages/admin/TVProjects";
import TVProjectEdit from "@/pages/admin/TVProjectEdit";
import Proposals from "@/pages/admin/Proposals";
import AdminReports from "@/pages/admin/Reports";
import AuditLog from "@/pages/admin/AuditLog";
import Admins from "@/pages/admin/Admins";
import Notifications from "@/pages/Notifications";

import RepDashboard from "@/pages/rep/Dashboard";
import CampaignBuilder from "@/pages/rep/CampaignBuilder";
import Campaigns from "@/pages/rep/Campaigns";
import TVCatalog from "@/pages/rep/TVCatalog";
import TVProjectDetail from "@/pages/rep/TVProjectDetail";
import Sponsorships from "@/pages/rep/Sponsorships";
import SubmitProposal from "@/pages/rep/SubmitProposal";
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
              <Route path="/admin/inventory" element={<BannerInventory />} />
              <Route path="/admin/proposals-review" element={<ProposalsReview />} />
              <Route path="/admin/tv-projects" element={<TVProjects />} />
              <Route path="/admin/tv-projects/:id" element={<TVProjectEdit />} />
              <Route path="/admin/proposals" element={<Proposals />} />
              <Route path="/admin/reports" element={<AdminReports />} />
              <Route path="/admin/audit-log" element={<AuditLog />} />
              <Route path="/admin/notifications" element={<Notifications />} />
              <Route path="/admin/admins" element={<OwnerOnly><Admins /></OwnerOnly>} />
            </Route>

            <Route element={<ProtectedRoute role="representative"><AppShell role="representative" /></ProtectedRoute>}>
              <Route path="/rep" element={<RepDashboard />} />
              <Route path="/rep/banners" element={<Campaigns />} />
              <Route path="/rep/banners/new" element={<CampaignBuilder />} />
              <Route path="/rep/tv" element={<TVCatalog />} />
              <Route path="/rep/tv/:id" element={<TVProjectDetail />} />
              <Route path="/rep/sponsorships" element={<Sponsorships />} />
              <Route path="/rep/proposals" element={<SubmitProposal />} />
              <Route path="/rep/proposals/new" element={<SubmitProposal />} />
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
