import { apiGet, apiPostForm, apiPostJson } from './client'
import type {
  AnalysisCreateRequest,
  AnalysisResponse,
  AnalysisScoreResponse,
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  ProgressResponse,
  QuestionResponse,
  RecommendationResponse,
  TopicResponse,
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

export function listQuestions(analysisId: string): Promise<QuestionResponse[]> {
  return apiGet<QuestionResponse[]>(`/analyses/${analysisId}/questions`)
}

export function listClos(analysisId: string): Promise<CloResponse[]> {
  return apiGet<CloResponse[]>(`/analyses/${analysisId}/clos`)
}

export function listTopics(analysisId: string): Promise<TopicResponse[]> {
  return apiGet<TopicResponse[]>(`/analyses/${analysisId}/topics`)
}

export function listAssessmentRecords(analysisId: string): Promise<AssessmentRecordResponse[]> {
  return apiGet<AssessmentRecordResponse[]>(`/analyses/${analysisId}/assessment-records`)
}

export function listFindings(analysisId: string): Promise<FindingResponse[]> {
  return apiGet<FindingResponse[]>(`/analyses/${analysisId}/findings`)
}

export function getAnalysisScore(analysisId: string): Promise<AnalysisScoreResponse> {
  return apiGet<AnalysisScoreResponse>(`/analyses/${analysisId}/score`)
}

export function listRecommendations(analysisId: string): Promise<RecommendationResponse[]> {
  return apiGet<RecommendationResponse[]>(`/analyses/${analysisId}/recommendations`)
}
