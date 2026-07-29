import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
import type { QuestionResponse } from '../../types/api'
import {
  independentlyScorableQuestions,
  sortQuestionsForFaculty,
} from './facultyOrdering'

export function QuestionsSection({ questions }: { questions: QuestionResponse[] }) {
  const { t } = useI18n()
  if (questions.length === 0) {
    return <p className="notice">{t('No questions were extracted for this analysis.')}</p>
  }
  const evaluatedQuestions = sortQuestionsForFaculty(
    independentlyScorableQuestions(questions),
  )
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
      <ResponsiveTable caption={t('Extracted questions')} className="questions-table">
        <thead>
          <tr>
            <th>{t('Question')}</th>
            <th>{t('Page')}</th>
            <th>{t('Marks')}</th>
            <th>{t('Text')}</th>
          </tr>
        </thead>
        <tbody>
          {evaluatedQuestions.map((question) => (
            <tr key={question.id}>
              <td><bdi>{question.number_label}</bdi></td>
              <td>{question.page_number}</td>
              <td>{question.marks ?? '—'}</td>
              <td><span dir="auto">{question.question_text}</span></td>
            </tr>
          ))}
        </tbody>
      </ResponsiveTable>
    </div>
  )
}
