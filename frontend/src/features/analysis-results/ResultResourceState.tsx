import type { ReactNode } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { useI18n } from '../../i18n/I18nProvider'
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
  const { t } = useI18n()
  if (resource.status === 'loading') {
    return <div className="results-resource-state" role="status" aria-busy="true">{loadingMessage}</div>
  }

  if (resource.status === 'error') {
    return (
      <Alert variant="error" title={errorTitle}>
        <p>{resource.message}</p>
        <Button variant="secondary" onClick={onRetry}>{t('Retry')}</Button>
      </Alert>
    )
  }

  return children(resource.data)
}
