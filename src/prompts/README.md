# Runtime Prompt Templates

Store application runtime prompt templates in this directory as implementation progresses.

Runtime prompts must:

- require structured output;
- prohibit invented CLOs, topics, evidence, and accreditation claims;
- return exactly one allowed status per applied rule;
- use `Not Verified` when evidence is insufficient;
- include source evidence and knowledge-base identifiers;
- be covered by tests before production use.
