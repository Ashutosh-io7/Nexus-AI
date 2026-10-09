import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import StatusPage from './pages/StatusPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<StatusPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App