# Exam Quality Analyzer — Demo Test Cases

This folder contains curated test cases for demonstrating and evaluating the Exam Quality Analyzer.

Each case includes:
- An Exam PDF
- A Course Specification PDF
- A specific expected quality scenario

These files are prepared for system testing and demonstration purposes.

---

## Case 00 — Clean Exam

**Course:** ITDB 211 — Database Systems  
**Exam Type:** Midterm

### Expected Behavior
This case represents a well-structured exam with no intentional quality issues.

The analyzer should identify:
- Correct total marks
- Consistent question numbering
- Valid question structure
- Appropriate CLO coverage
- Appropriate course-topic coverage
- No missing supporting references

**Purpose:** Demonstrates how the analyzer handles a valid exam without generating unnecessary quality issues.

---

## Case 01 — Arabic / Mixed-Language Exam with Missing Supporting Figure

**Course:** CS241 — Database Systems  
**Exam Type:** Final  
**Language:** Arabic / English Mixed

### Expected Behavior
The analyzer should identify:
- Arabic and English question content
- Parent and sub-question structure
- Figure 1 and link it to the relevant question
- Table 1 and link it to the relevant question
- A reference to Figure 5 where the actual figure is missing
- The missing supporting-material issue
- CLO and course-topic alignment from an Arabic/English Course Specification

**Purpose:** Demonstrates Arabic and mixed-language support, structured question extraction, supporting-material linking, and missing-reference detection.

---

## Case 02 — CLO Coverage Gap

**Course:** CPIT320 — Database Systems  
**Exam Type:** Midterm

### Expected Behavior
The analyzer should identify:
- Correct total marks
- Consistent numbering
- CLO1–CLO3 with supporting assessed questions
- CLO4 with no supporting assessed question

**Purpose:** Demonstrates question-to-CLO alignment and CLO coverage-gap detection.

---

## Case 03 — Linked Figure with Missing Mark

**Course:** CPIT370 — Computer Networks  
**Exam Type:** Final

### Expected Behavior
The analyzer should identify:
- Figure 3
- Correct links between Figure 3 and Q3(b) / Q3(c)
- Correct question hierarchy
- Consistent numbering
- A missing individual mark for Q3(c)

**Purpose:** Demonstrates supporting-figure detection and linking together with missing-mark validation.

---

## Recommended Testing Order

1. Case 00 — Clean Exam
2. Case 01 — Arabic / Mixed-Language + Missing Figure
3. Case 02 — CLO Coverage Gap
4. Case 03 — Linked Figure + Missing Mark

---

## Important Note

The analyzer provides an advisory academic quality review.

Its results are intended to support faculty review and do not replace final academic judgment or institutional quality-assurance procedures.
