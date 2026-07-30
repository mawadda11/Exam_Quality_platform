import type { RefObject } from 'react'
import { Drawer } from '../../components/ui/Drawer'
import { useI18n } from '../../i18n/I18nProvider'
import type { QuestionResponse } from '../../types/api'
import { sortQuestionReferences } from './facultyOrdering'
import {
  coverageStatus,
  facultyReason,
  matchingJudgments,
  relatedRows,
  type MappingTarget,
  type QuestionRelationshipRow,
} from './AlignmentCoverageSection'
import { StatusBadge } from './StatusBadge'

interface RelationshipMappingDrawerProps {
  target: MappingTarget | null
  rows: QuestionRelationshipRow[]
  onClose: () => void
  returnFocusRef?: RefObject<HTMLElement | null>
}

export function RelationshipMappingDrawer({
  target,
  rows,
  onClose,
  returnFocusRef,
}: RelationshipMappingDrawerProps) {
  const { locale, t } = useI18n()
  const isOpen = target !== null
  const record = target?.record
  const identifier =
    target?.kind === 'clo' ? target.record.code : (target?.record.code ?? t('Course Topic'))
  const text = record?.text ?? ''

  const matches = target ? relatedRows(rows, target.record, target.kind) : []
  const judgments = target
    ? matches.flatMap((row) => matchingJudgments(row, target.record, target.kind))
    : []
  const orderedReferences = target
    ? sortQuestionReferences(
        matches.map((row) => row.questionReference),
        matches
          .map((row) => row.question)
          .filter((question): question is QuestionResponse => question !== undefined),
      )
    : []
  const matchesByReference = new Map(matches.map((row) => [row.questionReference, row]))

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      titleId="mapping-details-title"
      returnFocusRef={returnFocusRef}
      title={
        <>
          {target?.kind === 'clo' ? t('CLO') : t('Course Topic')} <bdi>{identifier}</bdi>
        </>
      }
    >
      {target && (
        <>
          <section className="ui-drawer-section">
            <p dir="auto">{text}</p>
            <StatusBadge status={coverageStatus(judgments)} />
          </section>

          <section className="ui-drawer-section">
            <h3>{t('Linked questions')}</h3>
            {orderedReferences.length === 0 ? (
              <p>{t('None')}</p>
            ) : (
              <ul className="drawer-finding-list">
                {orderedReferences.map((reference) => {
                  const row = matchesByReference.get(reference)
                  if (!row) return null
                  const rowJudgments =
                    target.kind === 'clo' ? row.cloJudgments : row.topicJudgments
                  const relevantJudgments = matchingJudgments(row, target.record, target.kind)
                  const status = coverageStatus(relevantJudgments)
                  return (
                    <li key={reference} className="drawer-finding-item">
                      <div className="drawer-finding-header">
                        <strong>
                          <bdi>{reference}</bdi>
                        </strong>
                        <StatusBadge status={status} />
                      </div>
                      <p dir="auto">
                        {row.question?.question_text ?? t('Question text is unavailable.')}
                      </p>
                      <p>
                        {t('Marks')}: {row.question?.marks ?? '—'} · {t('Page')}{' '}
                        {row.question?.page_number ?? row.sourceEvidence?.page_number ?? '—'}
                      </p>
                      <p dir="auto">
                        <strong>{t('Relationship reason')}:</strong>{' '}
                        {rowJudgments
                          .map((judgment) => facultyReason(judgment.status, judgment.reasoning, locale, t))
                          .join(' ')}
                      </p>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          <p className="alignment-advisory-notice">
            {t(
              'The displayed relationships are analytical suggestions for review. They are not official mappings from the Course Specification and do not modify the original documents.',
            )}
          </p>
        </>
      )}
    </Drawer>
  )
}
