import { Link } from 'react-router-dom'
import { ProcessingStateBadge } from '../../components/ui/ProcessingStateBadge'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { routeForAnalysis } from '../../router/analysisRouting'
import type { AnalysisResponse } from '../../types/api'

interface AnalysisHistoryTableProps {
  analyses: AnalysisResponse[]
  caption: string
}

export function AnalysisHistoryTable({
  analyses,
  caption,
}: AnalysisHistoryTableProps) {
  return (
    <ResponsiveTable caption={caption}>
      <thead>
        <tr>
          <th scope="col">Course</th>
          <th scope="col">Course name</th>
          <th scope="col">Exam type</th>
          <th scope="col">Term</th>
          <th scope="col">Created</th>
          <th scope="col">Processing state</th>
          <th scope="col">Relationship</th>
          <th scope="col">Action</th>
        </tr>
      </thead>
      <tbody>
        {analyses.map((analysis) => (
          <tr key={analysis.id}>
            <th scope="row">
              <bdi>{analysis.course.code}</bdi>
            </th>
            <td dir="auto">{analysis.course.name}</td>
            <td>{analysis.exam_type}</td>
            <td>{analysis.term}</td>
            <td>{new Date(analysis.created_at).toLocaleDateString()}</td>
            <td>
              <ProcessingStateBadge state={analysis.state} />
            </td>
            <td>{analysis.predecessor_analysis_id ? 'Linked reanalysis' : 'Original'}</td>
            <td>
              <Link to={routeForAnalysis(analysis)}>Open analysis</Link>
            </td>
          </tr>
        ))}
      </tbody>
    </ResponsiveTable>
  )
}
