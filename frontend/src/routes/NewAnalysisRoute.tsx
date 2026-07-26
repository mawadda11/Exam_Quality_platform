import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { AnalysisWorkflowStepper } from '../features/analysis-upload/AnalysisWorkflowStepper'
import { AnalysisUploadFlow } from '../features/analysis-upload/AnalysisUploadFlow'

export function NewAnalysisRoute() {
  const navigate = useNavigate()

  return (
    <div className="route-stack route-content-form">
      <PageHeader
        title="New Analysis"
        description="Enter the exam information, upload both PDFs, then review and start."
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
