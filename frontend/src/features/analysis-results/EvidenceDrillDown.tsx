import { useI18n } from '../../i18n/I18nProvider'
import type { AcademicStatus, FindingEvidenceRef } from '../../types/api'
import type { EvidenceLookups } from './lookups'

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  question_text: 'Question text',
  marks: 'Marks',
  declared_total: 'Declared total',
  instructions: 'Instructions',
  clo: 'Course learning outcome',
  topic: 'Course topic',
  assessment_record: 'Assessment record',
  missing_section: 'Missing section',
  figure: 'Figure or illustration',
  table: 'Table',
  code: 'Code block',
  code_block: 'Code block',
  reference: 'Reference or citation',
  document_reference: 'Reference or citation',
  supporting_material: 'Supporting material',
}

export type EvidenceLookupKind = 'clo' | 'topic' | 'question'

interface ResolvedEvidence {
  label: string
  sourceText: string | null
  lookupKind: EvidenceLookupKind | null
}

function resolveEvidence(item: FindingEvidenceRef, lookups: EvidenceLookups): ResolvedEvidence {
  if (item.evidence_type === 'clo') {
    return { label: 'Course learning outcome', sourceText: lookups.cloByCode.get(item.item_reference)?.text ?? null, lookupKind: 'clo' }
  }
  if (item.evidence_type === 'topic') {
    return { label: 'Course topic', sourceText: lookups.topicByCode.get(item.item_reference)?.text ?? null, lookupKind: 'topic' }
  }
  if (item.evidence_type === 'question_text') {
    return {
      label: 'Question text',
      sourceText: lookups.questionByLabel.get(item.item_reference)?.question_text ?? null,
      lookupKind: 'question',
    }
  }
  return {
    label: EVIDENCE_TYPE_LABELS[item.evidence_type] ?? 'Evidence item',
    sourceText: null,
    lookupKind: null,
  }
}

interface EvidenceDrillDownProps {
  evidence: FindingEvidenceRef[]
  status: AcademicStatus
  lookups: EvidenceLookups
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
}

export function EvidenceDrillDown({ evidence, status, lookups, unavailableLookups = new Set() }: EvidenceDrillDownProps) {
  const { locale, t } = useI18n()
  if (evidence.length === 0) {
    return (
      <p className="evidence-empty">
        {status === 'Not Applicable'
          ? t('No evidence is linked — this rule does not apply in this case.')
          : t('No evidence was linked to this finding.')}
      </p>
    )
  }

  return (
    <ul className="evidence-list">
      {evidence.map((item) => {
        const resolved = resolveEvidence(item, lookups)
        const enrichmentUnavailable = resolved.lookupKind !== null && unavailableLookups.has(resolved.lookupKind)
        return (
          <li key={item.id} id={`evidence-${item.id}`} className="evidence-item">
            <dl>
              <div><dt>{t('Source')}</dt><dd>{item.source_document === 'exam' ? t('Exam') : t('Course Specification')}</dd></div>
              <div><dt>{t('Page')}</dt><dd>{item.page_number}</dd></div>
              <div><dt>{t('Evidence type')}</dt><dd>{t(resolved.label)}</dd></div>
              <div><dt>{t('Reference')}</dt><dd><bdi dir="auto">{item.item_reference}</bdi></dd></div>
            </dl>
            {resolved.sourceText && (
              <div className="evidence-source-text">
                <strong>{t('Original document excerpt')}</strong>
                <p lang={locale === 'ar' ? undefined : 'en'} dir="auto">{resolved.sourceText}</p>
                {locale === 'ar' && (
                  <p className="evidence-source-explanation">
                    {t('This source excerpt is preserved exactly as extracted and supports the linked finding.')}
                  </p>
                )}
              </div>
            )}
            {!resolved.sourceText && enrichmentUnavailable && (
              <p className="evidence-enrichment-note">
                {t('Referenced source text is unavailable because its extracted-data request failed.')}
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}
