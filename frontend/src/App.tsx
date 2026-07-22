import { DevIdentityBar } from './components/DevIdentityBar'
import { AnalysisUploadFlow } from './features/analysis-upload/AnalysisUploadFlow'

export function App() {
  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">Academic quality support</p>
        <h1>AI Exam Quality Platform</h1>
        <p>
          Upload a Midterm or Final exam and its populated TP-153 to create an evidence-based,
          traceable quality analysis.
        </p>
        <DevIdentityBar />
        <AnalysisUploadFlow />
      </section>
    </main>
  )
}
