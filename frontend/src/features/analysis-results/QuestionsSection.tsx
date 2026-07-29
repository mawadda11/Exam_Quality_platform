import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
import type { QuestionResponse } from '../../types/api'
import { sortQuestionsForFaculty } from './facultyOrdering'

export function QuestionsSection({ questions }: { questions: QuestionResponse[] }) {
  const { t } = useI18n()
  if (questions.length === 0) {
    return <p className="notice">{t('No questions were extracted for this analysis.')}</p>
  }
  const orderedQuestions = sortQuestionsForFaculty(questions)
  const childrenByParent = new Map<string, QuestionResponse[]>()
  for (const question of questions) {
    if (!question.parent_question_id) continue
    const children = childrenByParent.get(question.parent_question_id) ?? []
    children.push(question)
    childrenByParent.set(question.parent_question_id, children)
  }

  return (
    <div className="questions-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Questions')}</h2>
          <p>{questions.length} {t('extracted question records')}.</p>
        </div>
      </div>
      <ResponsiveTable caption={t('Extracted questions')} className="questions-table">
        <thead>
          <tr>
            <th>{t('Question')}</th>
            <th>{t('Type')}</th>
            <th>{t('Page')}</th>
            <th>{t('Marks')}</th>
            <th>{t('Text')}</th>
          </tr>
        </thead>
        <tbody>
          {orderedQuestions.map((question) => {
            const isContainer = (childrenByParent.get(question.id)?.length ?? 0) > 0
            return (
              <tr key={question.id}>
                <td><bdi>{question.number_label}</bdi></td>
                <td>{isContainer ? t('Parent / Container Question') : question.parent_question_id ? t('Child question') : t('Question')}</td>
                <td>{question.page_number}</td>
                <td>{question.marks ?? '—'}</td>
                <td><span dir="auto">{question.question_text}</span></td>
              </tr>
            )
          })}
        </tbody>
      </ResponsiveTable>
    </div>
  )
}
