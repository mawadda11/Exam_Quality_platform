# Paste or Import a Question List

This workflow is a fallback for exams that are difficult to parse automatically or for Faculty
Members who already have the questions in Word or Excel. It is not the primary workflow. Assisted
PDF extraction remains the recommended starting point so the reviewer corrects only the items that
need attention.

The original examination PDF and populated TP-153 are still required. The PDF remains the source
reference during Extraction Review.

## Fast paste workflow

1. Upload the examination PDF and matching populated TP-153.
2. Choose **Paste or import question list** on Review and Start.
3. Copy the numbered questions from Word or PDF and paste them into Extraction Review.
4. Keep each answer option on a separate line beginning with `A`, `B`, `C`, or `D`.
5. Import the pasted text, review the generated cards against the PDF, then save and confirm.

Example:

```text
Q1. Which pattern constructs a complex object step by step? [1 mark]
A. Singleton
B. Builder
C. Prototype
D. Adapter

Q2. Explain why hash collisions are undesirable. [2 marks]
```

The paste parser joins wrapped lines until the next numbered question. It extracts only explicit
marks such as `[2 marks]`, `(2 marks)`, or `[2]`. Technical values such as `GF (19)` are preserved as
question text and are not treated as marks.

## Simple CSV workflow

The CSV has only three required columns. Two optional columns make multiple-choice imports easier.

| Column | Required | Meaning |
|---|---:|---|
| `question_number` | Yes | Visible label, such as `Q1` |
| `question_text` | Yes | Complete question wording |
| `marks` | Yes as a column; cell may be empty | Enter only a mark visibly written in the exam |
| `question_type` | No | When empty, the platform infers a basic type |
| `options` | No | MCQ options in one cell separated by `|` |

Example:

```csv
question_number,question_text,marks,question_type,options
Q1,Which pattern constructs a complex object step by step?,1,,Singleton|Builder|Prototype|Adapter
Q2,Explain why hash collisions are undesirable.,2,short_answer,
```

Older detailed CSV files remain accepted for backward compatibility, but new users should use the
simple template.

## Governance rules

- The platform never invents marks. An empty marks cell remains unknown.
- The import never creates CLOs, topics, answers, correct options, or official mappings.
- Type and options are proposals that remain editable during review.
- The full PDF page shown on the left is the source reference; no separate automatic question crop
  is used.
- Academic analysis begins only after the exact question revision is saved and confirmed.
