import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AdminDashboard } from './pages/AdminDashboard'
import { LoginPage } from './pages/LoginPage'
import { ResellerDashboard } from './pages/ResellerDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute requiredRole="ADMIN">
              <AdminDashboard user={{ username: '', role: 'ADMIN' }} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reseller/dashboard"
          element={
            <ProtectedRoute requiredRole="RESELLER">
              <ResellerDashboard user={{ username: '', role: 'RESELLER' }} />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
