import { Link } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'

export function DashboardRoute() {
  return (
    <div className="route-stack route-content-compact">
      <PageHeader
        eyebrow="Academic quality support"
        title="Dashboard"
        description="Create a new evidence-based exam analysis or return to an existing analysis."
      />
      <Card as="section" className="route-card">
        <h2>Exam quality analyses</h2>
        <p>
          Every analysis uses one Midterm or Final exam PDF and its populated TP-153 Course
          Specification.
        </p>
        <div className="route-actions">
          <Link className="ui-button" to="/analyses/new">
            New Analysis
          </Link>
          <Link className="ui-button ui-button--secondary" to="/analyses">
            View Analyses
          </Link>
        </div>
      </Card>
    </div>
  )
}
