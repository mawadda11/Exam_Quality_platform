import type { QuestionResponse } from '../../types/api'

export function QuestionsSection({ questions }: { questions: QuestionResponse[] }) {
  if (questions.length === 0) {
    return <p className="notice">No questions were extracted for this analysis.</p>
  }

  return (
    <table className="questions-table">
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
            <td>{question.number_label}</td>
            <td>{question.page_number}</td>
            <td>{question.marks ?? '—'}</td>
            <td>{question.question_text}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
