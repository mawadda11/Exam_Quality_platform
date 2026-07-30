# Controlled Pilot — Known Limitations

This release candidate is intended only for a controlled pilot with approved Faculty Members,
synthetic or authorized documents, and active support. It is not a production deployment.

- The Exam Quality Analyzer supports evidence-based exam-quality review only. It does not evaluate
  the full academic program or establish program accreditation.
- Results depend on the completeness, readability, layout, and language quality of the uploaded
  exam and Course Specification.
- Missing, ambiguous, or unreliable evidence can produce Not Verified. This means the requirement
  could not be evaluated reliably; it is not a negative academic judgment.
- Suggested CLO, topic, and supporting-material relationships require Faculty Member review.
- OCR can omit or substitute text and may require manual correction in Extraction Review. Upload
  acceptance does not guarantee OCR accuracy.
- Original source wording and machine extraction are retained for traceability. Faculty corrections
  create review revisions and do not replace the original audit record.
- The analyzer does not issue accreditation, institutional approval, certification, pass, or fail
  decisions.
- Not every planned or policy-dependent check is enabled. The Methodology & Help page is the
  authoritative user-facing description of available and limited checks.
- External language-model integration is not part of this release. Pilot verification uses the
  governed local/offline behavior configured for the environment.
- Report-generation failures are not a substitute for analysis results and may require a retry.
- The pilot does not include institutional SSO, automated retention/deletion, malware scanning,
  production rate limiting, or an institutional audit/approval workflow.
- Production infrastructure remains separate. TLS termination, managed secrets, private object
  storage, backups/restore testing, monitoring, alerting, capacity limits, penetration testing, and
  an approved retention policy require deployment-owner decisions before production use.
- Automated tests do not replace manual bilingual visual, browser, accessibility, OCR, and PDF
  acceptance.

