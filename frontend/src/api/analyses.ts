import { apiGet, apiGetBlob, apiPostForm, apiPostJson } from './client'
import type {
  AnalysisCreateRequest,
  AnalysisResponse,
  AnalysisScoreResponse,
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  ProgressResponse,
  QuestionResponse,
  ReanalysisCreateRequest,
  RecommendationResponse,
  ReportResponse,
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

export function listAnalyses(): Promise<AnalysisResponse[]> {
  return apiGet<AnalysisResponse[]>('/analyses')
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

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string'
}

function isFindingResponse(value: unknown): value is FindingResponse {
  if (typeof value !== 'object' || value === null) return false
  const finding = value as Record<string, unknown>
  return (
    typeof finding.id === 'string' &&
    typeof finding.analysis_id === 'string' &&
    typeof finding.requirement_id === 'string' &&
    typeof finding.rule_id === 'string' &&
    isNullableString(finding.recommendation_id) &&
    typeof finding.status === 'string' &&
    typeof finding.explanation === 'string' &&
    typeof finding.confidence === 'number' &&
    typeof finding.evaluator_type === 'string' &&
    isNullableString(finding.ai_provider) &&
    isNullableString(finding.ai_model) &&
    isNullableString(finding.prompt_template_version) &&
    isNullableString(finding.kb_version) &&
    Array.isArray(finding.evidence)
  )
}

export function parseFindingResponses(value: unknown): FindingResponse[] {
  if (!Array.isArray(value) || !value.every(isFindingResponse)) {
    throw new Error('The server returned a malformed findings response.')
  }
  return value
}

export async function listFindings(analysisId: string): Promise<FindingResponse[]> {
  const response = await apiGet<unknown>(`/analyses/${analysisId}/findings`)
  return parseFindingResponses(response)
}

export function getAnalysisScore(analysisId: string): Promise<AnalysisScoreResponse> {
  return apiGet<AnalysisScoreResponse>(`/analyses/${analysisId}/score`)
}

export function listRecommendations(analysisId: string): Promise<RecommendationResponse[]> {
  return apiGet<RecommendationResponse[]>(`/analyses/${analysisId}/recommendations`)
}

export function generateReport(analysisId: string): Promise<ReportResponse> {
  return apiPostJson<ReportResponse>(`/analyses/${analysisId}/reports`, {})
}

export function listReports(analysisId: string): Promise<ReportResponse[]> {
  return apiGet<ReportResponse[]>(`/analyses/${analysisId}/reports`)
}

export function downloadReportFile(reportId: string): Promise<Blob> {
  return apiGetBlob(`/reports/${reportId}/download`)
}

export function createReanalysis(
  analysisId: string,
  payload: ReanalysisCreateRequest = {},
): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>(`/analyses/${analysisId}/reanalysis`, payload)
}

/** Triggers a browser download for an already-fetched Blob - a synthetic
 * anchor click is the standard way to do this once the file has to be
 * fetched manually (see apiGetBlob's docstring for why a plain <a href>
 * can't be used directly here). */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
