import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getAnalysisScore,
  getRuleCoverage,
  listAssessmentRecords,
  listClos,
  listFindings,
  listQuestions,
  listRecommendations,
  listReports,
  listTopics,
} from '../../api/analyses'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type {
  AnalysisScoreResponse,
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  QuestionResponse,
  RecommendationResponse,
  ReportResponse,
  RuleCoverageAuditResponse,
  TopicResponse,
} from '../../types/api'

export interface ResultsResourceData {
  questions: QuestionResponse[]
  clos: CloResponse[]
  topics: TopicResponse[]
  assessmentRecords: AssessmentRecordResponse[]
  findings: FindingResponse[]
  score: AnalysisScoreResponse
  recommendations: RecommendationResponse[]
  reports: ReportResponse[]
  ruleCoverage: RuleCoverageAuditResponse
}

export type ResultsResourceKey = keyof ResultsResourceData

export type ResultResource<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

export type AnalysisResultsResources = {
  [Key in ResultsResourceKey]: ResultResource<ResultsResourceData[Key]>
}

const RESOURCE_KEYS: ResultsResourceKey[] = [
  'questions',
  'clos',
  'topics',
  'assessmentRecords',
  'findings',
  'score',
  'recommendations',
  'reports',
  'ruleCoverage',
]

const LOADERS: {
  [Key in ResultsResourceKey]: (analysisId: string) => Promise<ResultsResourceData[Key]>
} = {
  questions: listQuestions,
  clos: listClos,
  topics: listTopics,
  assessmentRecords: listAssessmentRecords,
  findings: listFindings,
  score: getAnalysisScore,
  recommendations: listRecommendations,
  reports: listReports,
  ruleCoverage: getRuleCoverage,
}

const ERROR_MESSAGES: Record<ResultsResourceKey, string> = {
  questions: 'Could not load extracted questions.',
  clos: 'Could not load extracted CLOs.',
  topics: 'Could not load extracted topics.',
  assessmentRecords: 'Could not load extracted assessment records.',
  findings: 'Could not load findings.',
  score: 'Could not load the analysis score.',
  recommendations: 'Could not load recommendations.',
  reports: 'Could not load report history.',
  ruleCoverage: 'Could not load rule execution coverage.',
}

const pendingRequests = new Map<string, Promise<unknown>>()

function createLoadingResources(): AnalysisResultsResources {
  return {
    questions: { status: 'loading' },
    clos: { status: 'loading' },
    topics: { status: 'loading' },
    assessmentRecords: { status: 'loading' },
    findings: { status: 'loading' },
    score: { status: 'loading' },
    recommendations: { status: 'loading' },
    reports: { status: 'loading' },
    ruleCoverage: { status: 'loading' },
  }
}

function requestKey(analysisId: string, resource: ResultsResourceKey): string {
  return `${analysisId}:${resource}`
}

function loadOnce<Key extends ResultsResourceKey>(
  analysisId: string,
  resource: Key,
): Promise<ResultsResourceData[Key]> {
  const key = requestKey(analysisId, resource)
  const existing = pendingRequests.get(key) as Promise<ResultsResourceData[Key]> | undefined
  if (existing) return existing

  const request = LOADERS[resource](analysisId)
  pendingRequests.set(key, request)
  void request.then(
    () => {
      if (pendingRequests.get(key) === request) pendingRequests.delete(key)
    },
    () => {
      if (pendingRequests.get(key) === request) pendingRequests.delete(key)
    },
  )
  return request
}

function forceLoad<Key extends ResultsResourceKey>(
  analysisId: string,
  resource: Key,
): Promise<ResultsResourceData[Key]> {
  pendingRequests.delete(requestKey(analysisId, resource))
  return LOADERS[resource](analysisId)
}

interface StoredResultsState {
  analysisId: string
  resources: AnalysisResultsResources
}

interface AnalysisResultsData {
  resources: AnalysisResultsResources
  retryResource: (resource: ResultsResourceKey) => void
  refreshResource: <Key extends ResultsResourceKey>(
    resource: Key,
  ) => Promise<ResultsResourceData[Key]>
}

export function useAnalysisResultsData(analysisId: string): AnalysisResultsData {
  const { locale, t } = useI18n()
  const [stored, setStored] = useState<StoredResultsState>(() => ({
    analysisId,
    resources: createLoadingResources(),
  }))
  const activeAnalysisIdRef = useRef(analysisId)
  const mountedRef = useRef(false)
  const requestTokensRef = useRef<Record<ResultsResourceKey, number>>({
    questions: 0,
    clos: 0,
    topics: 0,
    assessmentRecords: 0,
    findings: 0,
    score: 0,
    recommendations: 0,
    reports: 0,
    ruleCoverage: 0,
  })
  const updateResource = useCallback(
    <Key extends ResultsResourceKey>(
      targetAnalysisId: string,
      resource: Key,
      next: ResultResource<ResultsResourceData[Key]>,
    ): void => {
      if (!mountedRef.current || activeAnalysisIdRef.current !== targetAnalysisId) return
      setStored((current) => {
        const resources =
          current.analysisId === targetAnalysisId
            ? current.resources
            : createLoadingResources()
        return {
          analysisId: targetAnalysisId,
          resources: { ...resources, [resource]: next },
        }
      })
    },
    [],
  )

  const runResource = useCallback(
    async <Key extends ResultsResourceKey>(
      targetAnalysisId: string,
      resource: Key,
      force: boolean,
      showLoading: boolean,
    ): Promise<ResultsResourceData[Key]> => {
      const token = requestTokensRef.current[resource] + 1
      requestTokensRef.current[resource] = token
      if (showLoading) updateResource(targetAnalysisId, resource, { status: 'loading' })

      try {
        const data = force
          ? await forceLoad(targetAnalysisId, resource)
          : await loadOnce(targetAnalysisId, resource)
        if (requestTokensRef.current[resource] === token) {
          updateResource(targetAnalysisId, resource, { status: 'ready', data })
        }
        return data
      } catch (error) {
        if (requestTokensRef.current[resource] === token) {
          updateResource(targetAnalysisId, resource, {
            status: 'error',
            message: localizeInterfaceError(error, locale, t, ERROR_MESSAGES[resource]),
          })
        }
        throw error
      }
    },
    [locale, t, updateResource],
  )

  useEffect(() => {
    activeAnalysisIdRef.current = analysisId
    mountedRef.current = true
    for (const resource of RESOURCE_KEYS) {
      void runResource(analysisId, resource, false, false).catch(() => undefined)
    }
    return () => {
      if (activeAnalysisIdRef.current === analysisId) mountedRef.current = false
    }
  }, [analysisId, runResource])

  const visibleResources = useMemo(
    () =>
      stored.analysisId === analysisId
        ? stored.resources
        : createLoadingResources(),
    [analysisId, stored],
  )

  const retryResource = useCallback(
    (resource: ResultsResourceKey): void => {
      if (visibleResources[resource].status !== 'error') return
      void runResource(analysisId, resource, false, true).catch(() => undefined)
    },
    [analysisId, runResource, visibleResources],
  )

  const refreshResource = useCallback(
    <Key extends ResultsResourceKey>(
      resource: Key,
    ): Promise<ResultsResourceData[Key]> =>
      runResource(analysisId, resource, true, true),
    [analysisId, runResource],
  )

  return { resources: visibleResources, retryResource, refreshResource }
}
