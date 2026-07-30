import { useMemo, useState } from 'react'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
import type { FindingResponse, QuestionResponse } from '../../types/api'
import { independentlyScorableQuestions, sortQuestionsForFaculty } from './facultyOrdering'
import { QuestionFilters } from './QuestionFilters'
import {
  buildQuestionRows,
  EMPTY_QUESTION_FILTERS,
  filterQuestionRows,
  type QuestionFilterValues,
} from './questionPresentation'
import type { ResultResource } from './useAnalysisResultsData'

interface QuestionsSectionProps {
  questions: QuestionResponse[]
  findings?: ResultResource<FindingResponse[]>
}

function readyData<T>(resource: ResultResource<T> | undefined, fallback: T): T {
  return resource?.status === 'ready' ? resource.data : fallback
}

export function QuestionsSection({
  questions,
  findings: findingsResource,
}: QuestionsSectionProps) {
  const { t } = useI18n()
  const [filters, setFilters] = useState<QuestionFilterValues>(EMPTY_QUESTION_FILTERS)

  const evaluatedQuestions = useMemo(
    () => sortQuestionsForFaculty(independentlyScorableQuestions(questions)),
    [questions],
  )
  const findings = readyData(findingsResource, [] as FindingResponse[])
  const rows = useMemo(
    () => buildQuestionRows(evaluatedQuestions, findings),
    [evaluatedQuestions, findings],
  )
  const filteredRows = useMemo(() => filterQuestionRows(rows, filters), [rows, filters])
  const hasFilters = filters.search !== ''

  if (questions.length === 0) {
    return <p className="notice">{t('No questions were extracted for this analysis.')}</p>
  }

  return (
    <div className="questions-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Questions')}</h2>
          <p>
            {evaluatedQuestions.length} {t('extracted question records')}.
          </p>
        </div>
      </div>

      <QuestionFilters
        values={filters}
        resultCount={filteredRows.length}
        totalCount={rows.length}
        onChange={setFilters}
      />

      {filteredRows.length === 0 ? (
        <div className="results-empty-state" role="status">
          <p>{t('No questions match the filters.')}</p>
        </div>
      ) : (
        <ResponsiveTable caption={t('Extracted questions')} className="questions-table">
          <thead>
            <tr>
              <th scope="col">{t('Question')}</th>
              <th scope="col">{t('Page')}</th>
              <th scope="col">{t('Marks')}</th>
              <th scope="col">{t('Text')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map(({ question }) => (
              <tr key={question.id}>
                <th scope="row" data-label={t('Question')}>
                  <bdi>{question.number_label}</bdi>
                </th>
                <td data-label={t('Page')}>{question.page_number}</td>
                <td data-label={t('Marks')}>{question.marks ?? '—'}</td>
                <td data-label={t('Text')}>
                  <span dir="auto">{question.question_text}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </ResponsiveTable>
      )}

      {hasFilters && filteredRows.length === 0 && (
        <p className="results-supporting-text">
          {t('Clear the filters to see every extracted question.')}
        </p>
      )}
    </div>
  )
}
