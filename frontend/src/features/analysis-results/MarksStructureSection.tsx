import type { FindingResponse } from '../../types/api'
import { MARKS_STRUCTURE_DIMENSIONS } from './dimensions'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'

interface MarksStructureSectionProps {
  findings: FindingResponse[]
  lookups: EvidenceLookups
}

export function MarksStructureSection({ findings, lookups }: MarksStructureSectionProps) {
  const relevant = findings.filter((finding) => MARKS_STRUCTURE_DIMENSIONS.has(finding.dimension))

  return (
    <div className="marks-structure-section">
      <h3>Marks & Structure</h3>
      {relevant.length === 0 ? (
        <p className="notice">No marks or structure findings are available yet.</p>
      ) : (
        <ul className="finding-list">
          {relevant.map((finding) => (
            <FindingCard key={finding.id} finding={finding} lookups={lookups} />
          ))}
        </ul>
      )}
    </div>
  )
}
