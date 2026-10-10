import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import ImportPage from './pages/ImportPage'
import Landing from './pages/Landing'
import StatusPage from './pages/StatusPage'
import CustomersPage from './pages/CustomersPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="/app/customers" replace />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="status" element={<StatusPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App