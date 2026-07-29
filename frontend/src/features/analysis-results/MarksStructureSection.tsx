import { useI18n } from '../../i18n/I18nProvider'
import type { FindingResponse } from '../../types/api'
import { MARKS_STRUCTURE_DIMENSIONS } from './dimensions'
import type { EvidenceLookupKind } from './EvidenceDrillDown'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'

interface MarksStructureSectionProps {
  findings: FindingResponse[]
  lookups: EvidenceLookups
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
}

export function MarksStructureSection({ findings, lookups }: MarksStructureSectionProps) {
  const { t } = useI18n()
  const relevant = findings.filter((finding) => MARKS_STRUCTURE_DIMENSIONS.has(finding.dimension))

  return (
    <div className="marks-structure-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Marks & Structure')}</h2>
          <p>{t('Review marks, totals, numbering, and question structure results.')}</p>
        </div>
      </div>
      {relevant.length === 0 ? (
        <p className="results-empty-state">{t('No marks or structure findings are available.')}</p>
      ) : (
        <ul className="finding-list">
          {relevant.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              lookups={lookups}
              showSpecializedLink={false}
              showDirectEvidence={false}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
