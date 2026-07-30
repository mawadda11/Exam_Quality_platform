const STORAGE_KEY = 'examQualityAccessToken'

export function getStoredAccessToken(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setStoredAccessToken(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token)
  } catch {
    // The current page remains authenticated in memory even when persistence
    // is unavailable (for example, restrictive private-browsing settings).
  }
}

export function clearStoredAccessToken(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing else to do when storage is unavailable.
  }
}
