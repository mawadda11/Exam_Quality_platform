import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { AnalysisWorkflowStepper } from '../features/analysis-upload/AnalysisWorkflowStepper'
import { AnalysisUploadFlow } from '../features/analysis-upload/AnalysisUploadFlow'
import { useI18n } from '../i18n/I18nProvider'

export function NewAnalysisRoute() {
  const { t } = useI18n()
  const navigate = useNavigate()

  return (
    <div className="route-stack route-content-form">
      <PageHeader
        title={t('New Analysis')}
        description={t('Enter the exam information, upload both PDFs, then review and start.')}
      />
      <div className="analysis-workflow-stepper">
        <AnalysisWorkflowStepper currentStep="information" />
      </div>
      <Card as="section" className="route-card">
        <AnalysisUploadFlow
          onCreated={(analysis) => navigate(`/analyses/${analysis.id}/documents`)}
        />
      </Card>
    </div>
  )
}
