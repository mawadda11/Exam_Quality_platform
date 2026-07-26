import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { AnalysisUploadFlow } from '../features/analysis-upload/AnalysisUploadFlow'

export function NewAnalysisRoute() {
  const navigate = useNavigate()

  return (
    <div className="route-stack route-content-form">
      <PageHeader
        title="New Analysis"
        description="Create the analysis record before uploading the required documents."
      />
      <Card as="section" className="route-card">
        <AnalysisUploadFlow
          onCreated={(analysis) => navigate(`/analyses/${analysis.id}/documents`)}
        />
      </Card>
    </div>
  )
}
