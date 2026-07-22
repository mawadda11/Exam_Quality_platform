import { apiGet, apiPostForm, apiPostJson } from './client'
import type {
  AnalysisCreateRequest,
  AnalysisResponse,
  ProgressResponse,
  UploadedFileResponse,
  UploadedFileType,
} from '../types/api'

export function createAnalysis(payload: AnalysisCreateRequest): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>('/analyses', payload)
}

export function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiGet<AnalysisResponse>(`/analyses/${analysisId}`)
}

export function uploadAnalysisFile(
  analysisId: string,
  fileType: UploadedFileType,
  file: File,
): Promise<UploadedFileResponse> {
  const form = new FormData()
  form.append('file_type', fileType)
  form.append('file', file)
  return apiPostForm<UploadedFileResponse>(`/analyses/${analysisId}/files`, form)
}

export function runAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>(`/analyses/${analysisId}/run`, {})
}

export function getAnalysisProgress(analysisId: string): Promise<ProgressResponse> {
  return apiGet<ProgressResponse>(`/analyses/${analysisId}/progress`)
}
