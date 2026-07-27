import { AuthProvider } from './features/auth/AuthProvider'
import { AppRoutes } from './router/AppRoutes'

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
