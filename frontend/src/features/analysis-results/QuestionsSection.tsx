import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import type { QuestionResponse } from '../../types/api'

export function QuestionsSection({ questions }: { questions: QuestionResponse[] }) {
  if (questions.length === 0) {
    return <p className="notice">No questions were extracted for this analysis.</p>
  }

  return (
    <ResponsiveTable caption="Extracted questions" className="questions-table">
      <thead>
        <tr>
          <th>Question</th>
          <th>Page</th>
          <th>Marks</th>
          <th>Text</th>
        </tr>
      </thead>
      <tbody>
        {questions.map((question) => (
          <tr key={question.id}>
            <td>
              <bdi>{question.number_label}</bdi>
            </td>
            <td>{question.page_number}</td>
            <td>{question.marks ?? '—'}</td>
            <td>
              <span dir="auto">{question.question_text}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </ResponsiveTable>
  )
}
