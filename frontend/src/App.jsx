import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/auth/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import { AuthProvider } from './context/AuthContext'
import CustomerProfilePage from './pages/CustomerProfilePage'
import CustomersPage from './pages/CustomersPage'
import ImportPage from './pages/ImportPage'
import Landing from './pages/Landing'
import LoginPage from './pages/LoginPage'
import ModelPage from './pages/ModelPage'
import PlaybookPage from './pages/PlaybookPage'
import StatusPage from './pages/StatusPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Application Shell */}
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<AppLayout />}>
              <Route index element={<Navigate to="/app/customers" replace />} />
              <Route path="customers" element={<CustomersPage />} />
              <Route path="customers/:customerId" element={<CustomerProfilePage />} />
              <Route path="import" element={<ImportPage />} />
              <Route path="status" element={<StatusPage />} />
              <Route path="model" element={<ModelPage />} />
              <Route path="playbook" element={<PlaybookPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App