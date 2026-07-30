import { AuthProvider } from './features/auth/AuthProvider'
import { I18nProvider } from './i18n/I18nProvider'
import { AppRoutes } from './router/AppRoutes'

export function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </I18nProvider>
  )
}
