import { apiGet } from './client'
import type {
  ReportLibraryPageResponse,
  ReportLibraryQuery,
  ReportResponse,
} from '../types/api'

export function listReportLibrary(
  query: ReportLibraryQuery = {},
): Promise<ReportLibraryPageResponse> {
  const parameters = new URLSearchParams()
  if (query.q) parameters.set('q', query.q)
  if (query.status) parameters.set('status', query.status)
  if (query.exam_type) parameters.set('exam_type', query.exam_type)
  if (query.language) parameters.set('language', query.language)
  if (query.sort) parameters.set('sort', query.sort)
  if (query.page) parameters.set('page', String(query.page))
  if (query.page_size) parameters.set('page_size', String(query.page_size))
  const suffix = parameters.size ? `?${parameters.toString()}` : ''
  return apiGet<ReportLibraryPageResponse>(`/reports${suffix}`)
}

export function getReportMetadata(reportId: string): Promise<ReportResponse> {
  return apiGet<ReportResponse>(`/reports/${reportId}`)
}
