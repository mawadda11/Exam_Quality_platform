import { apiGet, apiPostJson, apiPostNoContent } from './client'
import type {
  AuthSessionResponse,
  FacultyUserResponse,
  LoginRequest,
  MessageResponse,
  PasswordResetConfirmRequest,
  PasswordResetRequestResponse,
  RegisterRequest,
} from '../types/api'

export function registerFaculty(payload: RegisterRequest): Promise<AuthSessionResponse> {
  return apiPostJson<AuthSessionResponse>('/auth/register', payload)
}

export function loginFaculty(payload: LoginRequest): Promise<AuthSessionResponse> {
  return apiPostJson<AuthSessionResponse>('/auth/login', payload)
}

export function getCurrentFaculty(): Promise<FacultyUserResponse> {
  return apiGet<FacultyUserResponse>('/auth/me')
}

export function logoutFaculty(): Promise<void> {
  return apiPostNoContent('/auth/logout')
}

export function requestPasswordReset(email: string): Promise<PasswordResetRequestResponse> {
  return apiPostJson<PasswordResetRequestResponse>('/auth/password-reset/request', { email })
}

export function confirmPasswordReset(
  payload: PasswordResetConfirmRequest,
): Promise<MessageResponse> {
  return apiPostJson<MessageResponse>('/auth/password-reset/confirm', payload)
}
