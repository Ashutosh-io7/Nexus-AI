import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import ImportPage from './pages/ImportPage'
import Landing from './pages/Landing'
import StatusPage from './pages/StatusPage'
import CustomersPage from './pages/CustomersPage'
import CustomerProfilePage from './pages/CustomerProfilePage'
import ModelPage from './pages/ModelPage'
import PlaybookPage from './pages/PlaybookPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="/app/customers" replace />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:customerId" element={<CustomerProfilePage />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="status" element={<StatusPage />} />
          <Route path="model" element={<ModelPage />} />
          <Route path="playbook" element={<PlaybookPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App