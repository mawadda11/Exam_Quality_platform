import type { ReactNode } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import type { ResultResource } from './useAnalysisResultsData'

interface ResultResourceStateProps<T> {
  resource: ResultResource<T>
  loadingMessage: string
  errorTitle: string
  onRetry: () => void
  children: (data: T) => ReactNode
}

export function ResultResourceState<T>({
  resource,
  loadingMessage,
  errorTitle,
  onRetry,
  children,
}: ResultResourceStateProps<T>) {
  if (resource.status === 'loading') {
    return (
      <div className="results-resource-state" role="status" aria-busy="true">
        {loadingMessage}
      </div>
    )
  }

  if (resource.status === 'error') {
    return (
      <Alert variant="error" title={errorTitle}>
        <p>{resource.message}</p>
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      </Alert>
    )
  }

  return children(resource.data)
}
