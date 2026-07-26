import { DevIdentityBar } from './components/DevIdentityBar'
import { BrandMark } from './components/ui/BrandMark'
import { Card } from './components/ui/Card'
import { PageHeader } from './components/ui/PageHeader'
import { AnalysisUploadFlow } from './features/analysis-upload/AnalysisUploadFlow'

export function App() {
  return (
    <main className="shell">
      <Card as="section" className="card">
        <BrandMark />
        <PageHeader
          eyebrow="Academic quality support"
          title="AI Exam Quality Platform"
          description="Upload a Midterm or Final exam and its populated TP-153 to create an evidence-based, traceable quality analysis."
        />
        <DevIdentityBar />
        <AnalysisUploadFlow />
      </Card>
    </main>
  )
}
