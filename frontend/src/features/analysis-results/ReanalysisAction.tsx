import { useState } from 'react'
import { createReanalysis } from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type { AnalysisResponse } from '../../types/api'

interface ReanalysisActionProps {
  analysisId: string
  onCreated: (reanalysis: AnalysisResponse) => void
}

export function ReanalysisAction({ analysisId, onCreated }: ReanalysisActionProps) {
  const { locale, t } = useI18n()
  const [reuseTp153, setReuseTp153] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(): Promise<void> {
    setIsCreating(true)
    setError(null)
    try {
      const reanalysis = await createReanalysis(analysisId, { reuse_tp153: reuseTp153 })
      onCreated(reanalysis)
    } catch (err) {
      setError(localizeInterfaceError(err, locale, t, 'Could not create the reanalysis.'))
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Card as="section" className="reanalysis-action">
      <h2>{t('Analyze a revised exam')}</h2>
      <p>
        {t('Create a reanalysis linked to analysis')} <bdi>{analysisId}</bdi>.{' '}
        {t('This analysis and its reports remain unchanged.')}
      </p>
      <label className="reanalysis-reuse-option">
        <input
          type="checkbox"
          checked={reuseTp153}
          onChange={(event) => setReuseTp153(event.target.checked)}
        />
        {t('Reuse the previous Course Specification (uncheck to upload a new one)')}
      </label>
      <Button
        onClick={() => void handleCreate()}
        isLoading={isCreating}
        loadingLabel={t('Creating…')}
      >
        {t('Create Reanalysis')}
      </Button>
      {error && (
        <Alert variant="error" title={t('Could not create reanalysis')}>
          {error}
        </Alert>
      )}
    </Card>
  )
}
