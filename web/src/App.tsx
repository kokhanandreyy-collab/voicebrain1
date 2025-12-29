import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LandingPage from './pages/LandingPage';
import VerifyPage from './pages/VerifyPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import SettingsPage from './pages/SettingsPage';
import PricingPage from './pages/PricingPage';
import ShareReceivePage from './pages/ShareReceivePage';
import StatsPage from './pages/StatsPage';
import AdminLayout from './layouts/AdminLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import UsersPage from './pages/admin/UsersPage';
import PlansPage from './pages/admin/PlansPage';
import PromoCodesPage from './pages/admin/PromoCodesPage';
import PromptsPage from './pages/admin/PromptsPage';
import PrivacyPage from './pages/PrivacyPage';
import TermsPage from './pages/TermsPage';
import { GlobalSearch } from './components/GlobalSearch';
import { CookieBanner } from './components/CookieBanner';
import { ThemeProvider } from './context/ThemeContext';

function PrivateRoute({ children }: { children: JSX.Element }) {
    const token = localStorage.getItem('token');
    return token ? children : <Navigate to="/login" />;
}


function App() {
    return (
        <ThemeProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<LandingPage />} />
                    <Route path="/privacy" element={<PrivacyPage />} />
                    <Route path="/terms" element={<TermsPage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/verify" element={<VerifyPage />} />
                    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                    <Route path="/reset-password" element={<ResetPasswordPage />} />
                    <Route path="/dashboard" element={
                        <PrivateRoute>
                            <DashboardPage />
                        </PrivateRoute>
                    } />
                    <Route path="/settings" element={
                        <PrivateRoute>
                            <SettingsPage />
                        </PrivateRoute>
                    } />
                    <Route path="/settings/callback/:provider" element={
                        <PrivateRoute>
                            <SettingsPage />
                        </PrivateRoute>
                    } />
                    <Route path="/pricing" element={<PricingPage />} />
                    <Route path="/share-receive" element={
                        <PrivateRoute>
                            <ShareReceivePage />
                        </PrivateRoute>
                    } />
                    <Route path="/stats" element={
                        <PrivateRoute>
                            <StatsPage />
                        </PrivateRoute>
                    } />

                    {/* Admin Routes */}
                    <Route path="/admin" element={
                        <PrivateRoute>
                            <AdminLayout />
                        </PrivateRoute>
                    }>
                        <Route index element={<AdminDashboard />} />
                        <Route path="users" element={<UsersPage />} />
                        <Route path="plans" element={<PlansPage />} />
                        <Route path="promocodes" element={<PromoCodesPage />} />
                        <Route path="prompts" element={<PromptsPage />} />
                    </Route>
                </Routes>
                <GlobalSearch />
                <CookieBanner />
            </BrowserRouter>
        </ThemeProvider>
    );
}

export default App;
