/**
 * Local-development identity. NOT real authentication - mirrors the backend's
 * dev-only `X-Dev-User-Email` header adapter (see backend/app/core/identity.py).
 * Replace with a real sign-in flow before any non-development deployment.
 */

const STORAGE_KEY = 'devUserEmail'

export function getStoredDevUserEmail(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setStoredDevUserEmail(email: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, email)
  } catch {
    // localStorage unavailable (e.g. private browsing) - identity won't persist across reloads.
  }
}
