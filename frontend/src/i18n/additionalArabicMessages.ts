import { BATCH5_ARABIC_MESSAGES } from './batch5ArabicMessages'
import { BATCH5_REFINEMENT_ARABIC_MESSAGES } from './batch5RefinementArabicMessages'
import { METHODOLOGY_ARABIC_MESSAGES } from './methodologyArabicMessages'
import { PILOT_REFINEMENT_ARABIC_MESSAGES } from './pilotRefinementArabicMessages'
import { REPORTS_ARABIC_MESSAGES } from './reportsArabicMessages'
import { OCR_ARABIC_MESSAGES } from './ocrArabicMessages'

/**
 * Arabic presentation strings added during the Batch 3 bilingual UX completion.
 *
 * English source sentences remain the stable lookup keys so existing feature
 * code and API contracts do not change. A catalog audit test enforces that
 * every interface lookup has an Arabic value.
 */
export const ADDITIONAL_ARABIC_MESSAGES: Readonly<Record<string, string>> = {
  'Original source excerpt': 'النص المصدري الأصلي',
  'This source excerpt is preserved exactly as extracted and supports the linked finding.':
    'حُفظ هذا المقتطف كما استُخرج تمامًا، وهو يدعم نتيجة التقييم المرتبطة.',
  'The linked evidence supports the item-level judgment shown above.':
    'تدعم الأدلة المرتبطة الحكم التفصيلي المعروض أعلاه.',
  'The decision is based on the governed requirement and the evidence linked below.':
    'يستند القرار إلى المتطلب المحكوم والأدلة المرتبطة أدناه.',
  'Confidence reflects the quality and completeness of the linked evidence.':
    'يعكس مستوى الثقة جودة الأدلة المرتبطة واكتمالها.',
  CLOs: 'نواتج التعلم',
  'The stored files could not be validated. Check that both PDFs are available, then retry.':
    'تعذر التحقق من الملفات المحفوظة. تأكد من توفر ملفي PDF ثم أعد المحاولة.',
  'The examination could not be extracted. Review the PDF and retry.':
    'تعذر استخراج الاختبار. راجع ملف PDF ثم أعد المحاولة.',
  'The TP-153 Course Specification could not be extracted. Review the PDF and retry.':
    'تعذر استخراج توصيف المقرر TP-153. راجع ملف PDF ثم أعد المحاولة.',
  'The confirmed extraction could not be converted into analysis evidence. Retry the analysis.':
    'تعذر تحويل الاستخراج المؤكد إلى أدلة للتحليل. أعد محاولة التحليل.',
  'The controlled knowledge base could not be prepared. Retry the analysis.':
    'تعذر تجهيز قاعدة المعرفة المحكومة. أعد محاولة التحليل.',
  'The governed evaluation could not be completed. Retry the analysis.':
    'تعذر إكمال التقييم المحكوم. أعد محاولة التحليل.',
  'The analysis could not be finalized. Retry the analysis.':
    'تعذر إكمال التحليل. أعد محاولة التحليل.',
  'Report narrative and governed presentation wording use the selected language. Original source wording and evidence remain available for audit.':
    'تُعرض سردية التقرير والصياغات المحكومة باللغة المحددة، مع إبقاء النصوص المصدرية الأصلية والأدلة متاحة للتدقيق.',
  'Primary navigation': 'التنقل الرئيسي',
  'Faculty Member': 'عضو هيئة التدريس',
  'Signing out…': 'جارٍ تسجيل الخروج…',
  Platform: 'منصة التحليل',
  'Processing state': 'حالة المعالجة',
  'Current step': 'الخطوة الحالية',
  'Overall Exam Quality Score': 'الدرجة الإجمالية لجودة الاختبار',
  'Preliminary Local Quality Score': 'الدرجة المحلية الأولية لجودة الاختبار',
  'No applicable checks were available': 'لا توجد فحوصات منطبقة متاحة',
  'Based on 1 applicable check': 'استنادًا إلى فحص منطبق واحد',
  'Based on {count} applicable checks': 'استنادًا إلى {count} فحوصات منطبقة',
  '{count} local semantic suggestion(s) remain visible for review but are excluded from this preliminary score.':
    'تبقى {count} اقتراحات دلالية محلية ظاهرة للمراجعة لكنها مستبعدة من هذه الدرجة الأولية.',
  'Preliminary local result: {score}% based on {count} applicable checks.':
    'النتيجة المحلية الأولية: {score}% استنادًا إلى {count} فحوصات منطبقة.',
  'No verified checks were available': 'لا توجد فحوصات متحقق منها',
  'Based on 1 verified check': 'استنادًا إلى فحص واحد متحقق منه',
  'Based on {count} verified checks': 'استنادًا إلى {count} فحوصات متحقق منها',
  Course: 'المقرر',
  'Exam type': 'نوع الاختبار',
  Created: 'تاريخ الإنشاء',
  'Open analysis': 'فتح التحليل',
  'Analysis summary': 'ملخص التحليلات',
  'Total analyses': 'إجمالي التحليلات',
  'Completed analyses': 'التحليلات المكتملة',
  'Analyses needing attention': 'تحليلات تحتاج إلى مراجعة',
  'Reports available': 'التقارير المتاحة',
  Close: 'إغلاق',
  Question: 'السؤال',
  Page: 'الصفحة',
  'Question Text': 'نص السؤال',
  Marks: 'الدرجات',
  Status: 'الحالة',
  more: 'المزيد',
  Summary: 'ملخص',
  Evaluation: 'التقييم',
  Findings: 'النتائج',
  Evidence: 'الأدلة',
  'All CLOs': 'جميع نواتج التعلم',
  'All topics': 'جميع الموضوعات',
  'Search questions': 'البحث في الأسئلة',
  'Search by question ID or text': 'البحث برقم السؤال أو نصه',
  'Showing {shown} of {total} questions': 'عرض {shown} من أصل {total} سؤالًا',
  'Clear filters': 'مسح عوامل التصفية',
  'Filter questions': 'تصفية الأسئلة',
  'No questions match the filters.': 'لا توجد أسئلة مطابقة لعوامل التصفية.',
  'Clear the filters to see every extracted question.':
    'امسح عوامل التصفية لعرض جميع الأسئلة المستخرجة.',
  'Extracted Question Text': 'نص السؤال المستخرج',
  'Linked CLOs': 'نواتج التعلم المرتبطة',
  'Linked Course Topics': 'موضوعات المقرر المرتبطة',
  'CLO Analysis': 'تحليل نواتج التعلم',
  'Topic Analysis': 'تحليل موضوعات المقرر',
  'Linked questions': 'الأسئلة المرتبطة',
  'Total marks': 'إجمالي الدرجات',
  'A Midterm or Final exam may legitimately cover a subset of course topics. Topic coverage is informational and does not by itself indicate a quality problem.':
    'يجوز أن يغطي الاختبار النصفي أو النهائي جزءًا فقط من موضوعات المقرر بصورة مشروعة. تغطية الموضوعات معلوماتية ولا تشير وحدها إلى مشكلة في الجودة.',
  'Report Header': 'ترويسة التقرير',
  'Executive Summary': 'الملخص التنفيذي',
  'Status Distribution': 'توزيع الحالات',
  'Exam Summary': 'ملخص الاختبار',
  'Key Findings': 'أبرز النتائج',
  'Missing or Unverified Evidence': 'الأدلة المفقودة أو غير المتحقق منها',
  'Scope Disclaimer': 'إخلاء مسؤولية النطاق',
  'Technical Traceability Appendix': 'ملحق التتبع التقني',
  'Report language': 'لغة التقرير',
  Strengths: 'نقاط القوة',
  'Areas for Improvement': 'جوانب تحتاج إلى تحسين',
  Print: 'طباعة',
  'Independently scorable questions': 'الأسئلة القابلة للتقييم المستقل',
  'Missing or ambiguous references': 'الإحالات المفقودة أو الملتبسة',
  'This report analyzes the uploaded exam against the Course Specification, covering question clarity, CLO and topic alignment and coverage, marks and structure, and supporting materials.':
    'يحلل هذا التقرير الاختبار المرفوع مقارنةً بتوصيف المقرر، ويغطي وضوح الأسئلة، ومواءمة وتغطية نواتج التعلم والموضوعات، والدرجات والبنية، والمواد المساندة.',
  'Overall result: {score}% based on {count} verified applicable checks.':
    'النتيجة الإجمالية: {score}% استنادًا إلى {count} فحصًا منطبقًا تم التحقق منه.',
  'Overall result: {label}.': 'النتيجة الإجمالية: {label}.',
  'Strongest verified areas: {areas}.': 'أقوى الجوانب التي تم التحقق منها: {areas}.',
  'Main areas requiring improvement: {areas}.': 'أبرز الجوانب التي تحتاج إلى تحسين: {areas}.',
  '{count} result(s) could not be verified due to missing or unreliable evidence.':
    'تعذر التحقق من {count} نتيجة (نتائج) بسبب أدلة مفقودة أو غير موثوقة.',
  'Not Verified and Not Applicable results remain visible but are excluded from the score denominator.':
    'تظل نتائج «غير متحقق» و«غير منطبق» ظاهرة، لكنها مستبعدة من مقام الدرجة.',
  'This report applies only to the uploaded examination and the corresponding Course Specification. The platform does not issue accreditation decisions, does not evaluate the complete academic program, and does not replace academic judgment. The faculty member remains responsible for the final examination decision.':
    'يقتصر هذا التقرير على الاختبار المرفوع وتوصيف المقرر المطابق له. لا تصدر المنصة قرارات اعتماد، ولا تقيّم البرنامج الأكاديمي كاملًا، ولا تحل محل التقدير الأكاديمي. يظل عضو هيئة التدريس مسؤولًا عن القرار النهائي بشأن الاختبار.',
  'Review the exam quality report before downloading it.': 'راجع تقرير جودة الاختبار قبل تنزيله.',
  'Retrieving the governed analysis results…': 'جارٍ استرجاع نتائج التحليل المحكومة…',
  'Could not load the analysis.': 'تعذر تحميل التحليل.',
  'One or more governed results could not be loaded for this report.':
    'تعذر تحميل واحدة أو أكثر من النتائج المحكومة لهذا التقرير.',
  'Existing governed findings and source-faithful entities extracted from the TP-153.':
    'نتائج التقييم المحكومة والعناصر المستخرجة بأمانة من توصيف المقرر TP-153.',
  'Alignment and coverage findings': 'نتائج المواءمة والتغطية',
  'Loading alignment and coverage findings…': 'جارٍ تحميل نتائج المواءمة والتغطية…',
  'Could not load alignment and coverage findings': 'تعذر تحميل نتائج المواءمة والتغطية',
  'No alignment or coverage findings are available.': 'لا توجد نتائج مواءمة أو تغطية متاحة.',
  'Extracted CLOs': 'نواتج التعلم المستخرجة',
  'Loading extracted CLOs…': 'جارٍ تحميل نواتج التعلم المستخرجة…',
  'Could not load extracted CLOs': 'تعذر تحميل نواتج التعلم المستخرجة',
  'No CLOs were extracted from the TP-153.': 'لم تُستخرج نواتج تعلم من توصيف المقرر TP-153.',
  'TP-153 page': 'صفحة TP-153',
  'Extracted topics': 'موضوعات المقرر المستخرجة',
  'Loading extracted topics…': 'جارٍ تحميل موضوعات المقرر المستخرجة…',
  'Could not load extracted topics': 'تعذر تحميل موضوعات المقرر المستخرجة',
  'No topics were extracted from the TP-153.': 'لم تُستخرج موضوعات من توصيف المقرر TP-153.',
  'No code': 'دون رمز',
  'Extracted assessment records': 'سجلات التقييم المستخرجة',
  'These records are displayed as source evidence only. No mapping or consistency conclusion is inferred here.':
    'تُعرض هذه السجلات بوصفها أدلة مصدرية فقط، ولا يُستنتج منها هنا أي ربط أو حكم اتساق.',
  'Loading extracted assessment records…': 'جارٍ تحميل سجلات التقييم المستخرجة…',
  'Could not load extracted assessment records': 'تعذر تحميل سجلات التقييم المستخرجة',
  'No assessment records were extracted from the TP-153.':
    'لم تُستخرج سجلات تقييم من توصيف المقرر TP-153.',
  Method: 'الطريقة',
  Activity: 'النشاط',
  Percentage: 'النسبة',
  'Results sections': 'أقسام النتائج',
  'Loading score summary…': 'جارٍ تحميل ملخص الدرجة…',
  'Could not load score summary': 'تعذر تحميل ملخص الدرجة',
  'Loading extracted questions…': 'جارٍ تحميل الأسئلة المستخرجة…',
  'Could not load questions': 'تعذر تحميل الأسئلة',
  'Loading marks and structure findings…': 'جارٍ تحميل نتائج الدرجات والبنية…',
  'Could not load marks and structure findings': 'تعذر تحميل نتائج الدرجات والبنية',
  'Loading findings…': 'جارٍ تحميل النتائج…',
  'Could not load findings': 'تعذر تحميل النتائج',
  'Could not load extracted questions.': 'تعذر تحميل الأسئلة المستخرجة.',
  'Could not load extracted CLOs.': 'تعذر تحميل نواتج التعلم المستخرجة.',
  'Could not load extracted topics.': 'تعذر تحميل موضوعات المقرر المستخرجة.',
  'Could not load extracted assessment records.': 'تعذر تحميل سجلات التقييم المستخرجة.',
  'Could not load findings.': 'تعذر تحميل النتائج.',
  'Could not load the analysis score.': 'تعذر تحميل درجة التحليل.',
  'Could not load recommendations.': 'تعذر تحميل التوصيات.',
  'Could not load report history.': 'تعذر تحميل سجل التقارير.',
  'Could not load rule execution coverage.': 'تعذر تحميل تغطية تنفيذ القواعد.',
  'No evidence is linked — this rule does not apply in this case.':
    'لا يوجد دليل مرتبط؛ لأن هذه القاعدة لا تنطبق في هذه الحالة.',
  'No evidence was linked to this finding.': 'لم يُربط أي دليل بهذه النتيجة.',
  Source: 'المصدر',
  Exam: 'الاختبار',
  'Evidence type': 'نوع الدليل',
  Reference: 'المرجع',
  'Referenced source text is unavailable because its extracted-data request failed.':
    'النص المصدري المشار إليه غير متاح بسبب تعذر تحميل البيانات المستخرجة.',
  Requirement: 'المتطلب',
  Rule: 'القاعدة',
  Provider: 'المزوّد',
  Model: 'النموذج',
  Prompt: 'قالب التعليمات',
  KB: 'قاعدة المعرفة',
  'Semantic evaluation details': 'تفاصيل التقييم الدلالي',
  For: 'موجّه إلى',
  'Filter findings': 'تصفية النتائج',
  'All statuses': 'جميع الحالات',
  'All questions': 'جميع الأسئلة',
  Dimension: 'البُعد',
  'All dimensions': 'جميع الأبعاد',
  'Showing {shown} of {total} findings': 'عرض {shown} من أصل {total} نتيجة',
  'Reset filters': 'إعادة تعيين عوامل التصفية',
  'Filter the findings already returned for this analysis.':
    'صفِّ نتائج التقييم المعادة لهذا التحليل.',
  'Loading recommendations…': 'جارٍ تحميل التوصيات…',
  'Could not load recommendations': 'تعذر تحميل التوصيات',
  'Findings remain available, but their recommendation records could not be loaded.':
    'لا تزال النتائج متاحة، لكن تعذر تحميل سجلات توصياتها.',
  'Retry recommendations': 'إعادة محاولة تحميل التوصيات',
  'Missing Evidence': 'أدلة مفقودة',
  'These findings are excluded from the score because evidence was missing, unreadable, or insufficient—not because the exam failed the requirement.':
    'استُبعدت هذه النتائج من الدرجة لأن الأدلة مفقودة أو غير مقروءة أو غير كافية، وليس لأن الاختبار لم يستوفِ المتطلب.',
  'No findings are available.': 'لا توجد نتائج متاحة.',
  'No findings match the selected filters.': 'لا توجد نتائج تطابق عوامل التصفية المحددة.',
  'Governed findings returned by the existing evaluation pipeline.':
    'نتائج محكومة أعادها مسار التقييم المعتمد.',
  'No marks or structure findings are available.': 'لا توجد نتائج متاحة للدرجات أو البنية.',
  'A summary of the quality checks completed for this exam.':
    'ملخص لفحوصات الجودة المكتملة لهذا الاختبار.',
  'Evaluation results': 'نتائج التقييم',
  'About this score': 'حول هذه الدرجة',
  'This score summarizes the checks the platform was able to verify for this exam.':
    'تلخص هذه الدرجة الفحوصات التي أمكن التحقق منها لهذا الاختبار.',
  'Results that could not be verified or did not apply remain visible, but they do not lower the score. Checks that are not yet available are also excluded.':
    'تظل النتائج التي تعذر التحقق منها أو لم تنطبق ظاهرة، لكنها لا تخفض الدرجة. كما تُستبعد الفحوصات غير المتاحة حاليًا.',
  'No questions were extracted for this analysis.': 'لم تُستخرج أسئلة لهذا التحليل.',
  'extracted question records': 'سجلات الأسئلة المستخرجة',
  'Extracted questions': 'الأسئلة المستخرجة',
  Type: 'النوع',
  Text: 'النص',
  'Parent / Container Question': 'سؤال رئيسي / حاوية',
  'Creating…': 'جارٍ الإنشاء…',
  'Could not generate the report.': 'تعذر إنشاء التقرير.',
  'The report was generated and report history was refreshed.':
    'تم إنشاء التقرير وتحديث سجل التقارير.',
  'The report was generated, but report history could not be refreshed. Retry the history request.':
    'تم إنشاء التقرير، لكن تعذر تحديث سجل التقارير. أعد محاولة تحميل السجل.',
  'Could not download the report.': 'تعذر تنزيل التقرير.',
  'Generate and download report snapshots for analysis':
    'إنشاء نسخ تقارير ثابتة وتنزيلها للتحليل',
  'Static report headings are localized. Official knowledge-base wording and source evidence remain in their governed source language.':
    'تُعرض عناوين التقرير ومحتواه المحكوم باللغة المحددة، مع الاحتفاظ بالنصوص المصدرية الأصلية للتتبع.',
  'Report action could not be completed': 'تعذر إكمال إجراء التقرير',
  'Report history could not be loaded': 'تعذر تحميل سجل التقارير',
  Retry: 'إعادة المحاولة',
  'Return to Analyses': 'العودة إلى التحليلات',
  'Last updated': 'آخر تحديث',
  'Exam file': 'ملف الاختبار',
  'Not available': 'غير متاح',
  'TP-153 file': 'ملف TP-153',
  'Loading score…': 'جارٍ تحميل الدرجة…',
  'Retry score': 'إعادة محاولة تحميل الدرجة',
  'Analysis execution needs attention': 'يتطلب تنفيذ التحليل الانتباه',
  'Supported checks did not complete. This is a system execution issue, not an academic result.':
    'لم تكتمل الفحوصات المدعومة. هذه مشكلة تنفيذ في النظام وليست نتيجة أكاديمية.',
  'Analysis completed with a limited check': 'اكتمل التحليل مع فحص محدود',
  'Some supported checks could not be fully evaluated. This does not count as an exam failure.':
    'تعذر تقييم بعض الفحوصات المدعومة بالكامل، ولا يُعد ذلك إخفاقًا للاختبار.',
  'Analysis completed successfully': 'اكتمل التحليل بنجاح',
  'All checks supported for this analysis completed successfully.':
    'اكتملت بنجاح جميع الفحوصات المدعومة لهذا التحليل.',
  'Analysis completion': 'اكتمال التحليل',
  'Checking analysis completion…': 'جارٍ التحقق من اكتمال التحليل…',
  'Could not confirm analysis completion': 'تعذر التحقق من اكتمال التحليل',
  'Retry completion check': 'إعادة محاولة فحص الاكتمال',
  'See what the platform evaluates': 'عرض نطاق التقييم',
  'This category is not a score, severity, priority, or probability.':
    'هذا التصنيف ليس درجة أو شدة أو أولوية أو احتمالًا.',
  'Semantic confidence': 'الثقة الدلالية',
  page: 'صفحة',
  'Evidence reference unavailable in this response': 'مرجع الدليل غير متاح في هذه الاستجابة',
  'This relationship is an analysis output. It is not an official TP-153 mapping and does not overwrite source evidence.':
    'هذه العلاقة ناتج تحليلي، وليست ربطًا رسميًا في TP-153، ولا تستبدل أدلة المصدر.',
  'Source evidence': 'دليل المصدر',
  'No target relationship was asserted.': 'لم تُثبت علاقة مع هدف.',
  'Concise reasoning': 'التعليل المختصر',
  'Governed decision reasoning': 'تعليل القرار المحكوم',
  'Confidence basis': 'أساس الثقة',
  'Evidence-linked item judgments': 'أحكام العناصر المرتبطة بالأدلة',
  'No item-level relationship or judgment was retained for this finding.':
    'لم يُحتفظ بعلاقة أو حكم على مستوى العناصر لهذه النتيجة.',
  'Controlled KB references': 'مراجع قاعدة المعرفة المحكومة',
  "This requirement's official source classification, from the versioned knowledge base.":
    'تصنيف المصدر الرسمي لهذا المتطلب من قاعدة المعرفة ذات الإصدار المحدد.',
  'Could not create analysis': 'تعذر إنشاء التحليل',
  'Exam Information': 'معلومات الاختبار',
  'Enter the course and exam details. These details become read-only after creation.':
    'أدخل بيانات المقرر والاختبار. تصبح هذه البيانات للقراءة فقط بعد الإنشاء.',
  'Check the exam information': 'تحقق من معلومات الاختبار',
  'Correct the highlighted fields and try again.': 'صحح الحقول المحددة ثم أعد المحاولة.',
  'e.g. 2026 Spring': 'مثال: ربيع 2026',
  'Continue to Upload Documents': 'المتابعة إلى رفع المستندات',
  'Both the examination PDF and the populated TP-153 are required. Each upload can be retried independently.':
    'يلزم رفع ملف الاختبار وملف TP-153 المعبأ بصيغة PDF، ويمكن إعادة محاولة كل ملف بصورة مستقلة.',
  'Arabic, English, and mixed examination and TP-153 PDF files are supported.':
    'تُدعم ملفات الاختبار وTP-153 العربية والإنجليزية والمختلطة بصيغة PDF.',
  'Persisted exam information': 'معلومات الاختبار المحفوظة',
  'Examination PDF': 'ملف الاختبار PDF',
  'Select the Midterm or Final examination PDF.': 'اختر ملف الاختبار النصفي أو النهائي بصيغة PDF.',
  'Populated TP-153': 'ملف TP-153 المعبأ',
  'Select the populated course specification PDF.': 'اختر ملف توصيف المقرر المعبأ بصيغة PDF.',
  'Documents ready': 'المستندات جاهزة',
  'The refreshed analysis confirms that both required documents are uploaded. Continue when you are ready to review and start.':
    'يؤكد التحليل المحدّث رفع المستندين المطلوبين. تابع عندما تكون مستعدًا للمراجعة والبدء.',
  'Upload both PDFs to continue. If this page is refreshed before a selected file is uploaded, the browser will require you to select that file again.':
    'ارفع ملفي PDF للمتابعة. إذا حُدثت الصفحة قبل رفع ملف محدد، فسيطلب المتصفح اختياره مرة أخرى.',
  'New analysis progress': 'تقدم التحليل الجديد',
  'The selected file must be a PDF.': 'يجب أن يكون الملف المحدد بصيغة PDF.',
  'The upload was accepted, but the analysis status could not be refreshed.':
    'تم قبول الرفع، لكن تعذر تحديث حالة التحليل.',
  'Upload failed. Please try again.': 'فشل رفع الملف. أعد المحاولة.',
  Select: 'اختيار',
  'No PDF selected.': 'لم يتم تحديد ملف PDF.',
  Selected: 'المحدد',
  'Uploading…': 'جارٍ الرفع…',
  Uploaded: 'تم الرفع',
  'The upload response was received. The refreshed analysis has not yet confirmed readiness.':
    'تم استلام استجابة الرفع، ولم يؤكد التحليل المحدّث الجاهزية بعد.',
  'Retry upload': 'إعادة محاولة الرفع',
  'Upload PDF': 'رفع ملف PDF',
  'Refreshing…': 'جارٍ التحديث…',
  'Retry status refresh': 'إعادة محاولة تحديث الحالة',
  'Could not start analysis': 'تعذر بدء التحليل',
  'Retry accepted': 'تم قبول إعادة المحاولة',
  'Processing stages': 'مراحل المعالجة',
  'Progress could not be refreshed. Polling will retry automatically.':
    'تعذر تحديث التقدم. ستُعاد المحاولة تلقائيًا.',
  'The extracted Exam and TP-153 evidence is ready. Continue to the dedicated review workspace to correct transcription, save a revision, and confirm it.':
    'أصبحت أدلة الاختبار وTP-153 المستخرجة جاهزة. انتقل إلى مساحة المراجعة لتصحيح النسخ وحفظ نسخة ومراجعتها.',
  'Not uploaded': 'غير مرفوع',
  'Review and Start': 'المراجعة والبدء',
  'Confirm the persisted details and uploaded documents before starting the analysis.':
    'تحقق من البيانات المحفوظة والمستندات المرفوعة قبل بدء التحليل.',
  'Scope reminder': 'تذكير بالنطاق',
  'The analysis applies only to this uploaded examination and its corresponding populated TP-153. Starting the analysis does not issue an accreditation or institutional decision.':
    'يقتصر التحليل على الاختبار المرفوع وملف TP-153 المعبأ المقابل له، ولا يصدر بدء التحليل قرار اعتماد أو قرارًا مؤسسيًا.',
  'Checking your session': 'جارٍ التحقق من جلستك',
  'Please wait…': 'يرجى الانتظار…',
  'extraction confidence': 'ثقة الاستخراج',
  'Include in analysis': 'تضمين في التحليل',
  'Restore machine value': 'استعادة القيمة المستخرجة',
  No: 'لا توجد',
  'The empty collection is preserved as source evidence; do not create replacement official records here.':
    'تُحفظ المجموعة الفارغة بوصفها دليلًا مصدريًا؛ لا تنشئ سجلات رسمية بديلة هنا.',
  'This structural question groups the sub-questions below and is not scored as an independent semantic item.':
    'يجمع هذا السؤال البنيوي الأسئلة الفرعية أدناه، ولا يُقيّم بوصفه عنصرًا دلاليًا مستقلًا.',
  'Sub-question marks total': 'مجموع درجات الأسئلة الفرعية',
  'The section total is authoritative; individual child marks may remain blank.':
    'درجة القسم هي المعتمدة، ويمكن أن تبقى درجات الأسئلة الفرعية الفردية فارغة.',
  'Covered by section total': 'مشمولة في درجة القسم',
  'Review summary': 'ملخص المراجعة',
  'assessed questions': 'أسئلة خاضعة للتقييم',
  'structural containers': 'حاويات بنيوية',
  'questions needing review': 'أسئلة تحتاج إلى مراجعة',
  'true blockers': 'عوائق فعلية',
  'Confirmation availability': 'إتاحة التأكيد',
  'Available now': 'متاح الآن',
  'Available after saving this revision': 'متاح بعد حفظ هذه النسخة',
  'Not available yet': 'غير متاح بعد',
  'Review flagged questions': 'مراجعة الأسئلة المشار إليها',
  'Needs review': 'يحتاج إلى مراجعة',
  'Why this question needs review': 'سبب احتياج هذا السؤال إلى المراجعة',
  'Check the section and child marks against the PDF.':
    'تحقق من درجة القسم ودرجات الأسئلة الفرعية بمقارنتها بملف PDF.',
  'Check that this question is attached to the correct section.':
    'تحقق من ارتباط هذا السؤال بالقسم الصحيح.',
  'Check this question number against the PDF.':
    'تحقق من رقم هذا السؤال بمقارنته بملف PDF.',
  'Check the shared instructions for this question.':
    'تحقق من التعليمات المشتركة لهذا السؤال.',
  'Check the technical text and symbols against the PDF.':
    'تحقق من النص التقني والرموز بمقارنتها بملف PDF.',
  'Check that the correct figure belongs with this question.':
    'تحقق من ارتباط الشكل الصحيح بهذا السؤال.',
  'Check this question against the PDF because extraction confidence is lower.':
    'تحقق من هذا السؤال بمقارنته بملف PDF لأن ثقة الاستخراج منخفضة.',
  'Confirm the question type manually against the PDF.':
    'تحقق يدويًا من نوع السؤال بمقارنته بملف PDF.',
  'Check this question against the original PDF.':
    'تحقق من هذا السؤال بمقارنته بملف PDF الأصلي.',
  'Technical extraction details': 'تفاصيل الاستخراج التقنية',
  'These records are grouped by type and page for audit. Review recommendations do not block confirmation unless listed above.':
    'جُمعت هذه السجلات حسب النوع والصفحة لأغراض التدقيق. لا تمنع توصيات المراجعة التأكيد ما لم تكن مدرجة أعلاه.',
  record: 'سجل',
  records: 'سجلات',
  'Question number': 'رقم السؤال',
  'Question text': 'نص السؤال',
  'CLO code': 'رمز ناتج التعلم',
  'Program outcome reference': 'مرجع ناتج البرنامج',
  'CLO text': 'نص ناتج التعلم',
  'Topic code': 'رمز الموضوع',
  'Expected hours': 'الساعات المتوقعة',
  'Topic text': 'نص الموضوع',
  'Could not load extraction review': 'تعذر تحميل مراجعة الاستخراج',
  'Loading extraction review': 'جارٍ تحميل مراجعة الاستخراج',
  'Retrieving the immutable review revision and source anchors…':
    'جارٍ استرجاع نسخة المراجعة غير القابلة للتغيير ومراجع المصدر…',
  'The extraction review is unavailable.': 'مراجعة الاستخراج غير متاحة.',
  'Retry review': 'إعادة محاولة تحميل المراجعة',
  Topics: 'الموضوعات',
  Revision: 'النسخة',
  saved: 'محفوظة',
  'Could not save the extraction review.': 'تعذر حفظ مراجعة الاستخراج.',
  'Could not confirm the extraction review.': 'تعذر تأكيد مراجعة الاستخراج.',
  'Transcription review only': 'مراجعة النسخ فقط',
  'Correct only what is visibly present in the uploaded Exam and TP-153. Confirmation does not approve academic alignment and does not create missing official course information.':
    'صحح فقط ما يظهر في الاختبار وTP-153 المرفوعين. لا يعني التأكيد اعتماد المواءمة الأكاديمية ولا ينشئ معلومات رسمية مفقودة للمقرر.',
  'Extraction review revision status': 'حالة نسخة مراجعة الاستخراج',
  'Unsaved changes': 'تغييرات غير محفوظة',
  Confirmed: 'مؤكدة',
  'Open for review': 'مفتوحة للمراجعة',
  'Items requiring attention': 'عناصر تتطلب الانتباه',
  'Confirmation unavailable': 'التأكيد غير متاح',
  'Review action failed': 'تعذر إجراء المراجعة',
  'Review saved': 'تم حفظ المراجعة',
  'Review Extraction': 'مراجعة الاستخراج',
  'Save this revision before confirming.': 'احفظ هذه النسخة قبل التأكيد.',
  'Revision is saved.': 'تم حفظ النسخة.',
  'Confirmation permanently closes extraction editing for this analysis.':
    'يؤدي التأكيد إلى إغلاق تعديل الاستخراج نهائيًا لهذا التحليل.',
  'Saving revision…': 'جارٍ حفظ النسخة…',
  'Save New Revision': 'حفظ نسخة جديدة',
  'Confirming…': 'جارٍ التأكيد…',
  'Open an existing analysis or begin a new one.': 'افتح تحليلًا قائمًا أو ابدأ تحليلًا جديدًا.',
  'Loading analyses': 'جارٍ تحميل التحليلات',
  'Retrieving your analyses…': 'جارٍ استرجاع تحليلاتك…',
  'Could not load analyses': 'تعذر تحميل التحليلات',
  'Retry analyses': 'إعادة محاولة تحميل التحليلات',
  'No analyses yet': 'لا توجد تحليلات بعد',
  'Create an analysis to upload an exam and its populated TP-153.':
    'أنشئ تحليلًا لرفع اختبار وملف TP-153 المعبأ المقابل له.',
  'Could not load this analysis.': 'تعذر تحميل هذا التحليل.',
  'No analysis identifier was provided.': 'لم يتم توفير معرّف للتحليل.',
  'Could not open analysis': 'تعذر فتح التحليل',
  'Loading analysis': 'جارٍ تحميل التحليل',
  'Retrieving the selected analysis…': 'جارٍ استرجاع التحليل المحدد…',
  'Retry analysis': 'إعادة محاولة تحميل التحليل',
  'Upload the examination PDF and populated TP-153 required by this analysis.':
    'ارفع ملف الاختبار وملف TP-153 المعبأ المطلوبين لهذا التحليل.',
  'Review the persisted information and explicitly start the analysis when ready.':
    'راجع المعلومات المحفوظة وابدأ التحليل صراحةً عندما تصبح جاهزًا.',
  'Back to Upload Documents': 'العودة إلى رفع المستندات',
  'Review Extracted Evidence': 'مراجعة المحتوى المستخرج',
  'Correct source transcription, exclude false positives, and confirm the exact revision before academic analysis begins.':
    'صحح نسخ المصدر واستبعد العناصر غير الصحيحة وأكد النسخة المحددة قبل بدء التحليل الأكاديمي.',
  'Processing continues through the existing backend workflow.':
    'تستمر المعالجة عبر مسار العمل المعتمد.',
  'Create a new evidence-based exam analysis or return to an existing analysis.':
    'أنشئ تحليلًا جديدًا قائمًا على الأدلة أو عد إلى تحليل قائم.',
  'Loading dashboard': 'جارٍ تحميل لوحة التحكم',
  'Could not load dashboard': 'تعذر تحميل لوحة التحكم',
  'Retry dashboard': 'إعادة محاولة تحميل لوحة التحكم',
  'Recent analyses': 'أحدث التحليلات',
  'View all analyses': 'عرض جميع التحليلات',
  'What the Platform Evaluates': 'نطاق التقييم',
  'See which exam-quality checks are available, which check has a defined limitation, and which capabilities are planned. Planned checks are not treated as exam failures and do not reduce the score.':
    'تعرّف على فحوصات جودة الاختبار المتاحة والفحص ذي القيد المحدد والقدرات المخطط لها. لا تُعد الفحوصات المخطط لها إخفاقًا للاختبار ولا تخفض الدرجة.',
  'Current evaluation scope summary': 'ملخص نطاق التقييم الحالي',
  'Available checks': 'الفحوصات المتاحة',
  'Check with a defined limitation': 'فحص بقيد محدد',
  'Planned checks': 'الفحوصات المخطط لها',
  'These checks can produce an academic result when the uploaded exam and TP-153 contain sufficient confirmed evidence.':
    'يمكن لهذه الفحوصات إنتاج نتيجة أكاديمية عندما يتضمن الاختبار وTP-153 أدلة مؤكدة كافية.',
  'Available with a defined limitation': 'متاح بقيد محدد',
  'This check is supported only for the documented cases below. The system does not invent a threshold for cases that require an approved academic method.':
    'يُدعم هذا الفحص للحالات الموثقة أدناه فقط، ولا يفترض النظام حدًا للحالات التي تتطلب طريقة أكاديمية معتمدة.',
  'Planned capabilities': 'القدرات المخطط لها',
  'These checks remain documented so the platform does not hide its current boundaries. They are not scored and are not shown as failures in an individual exam result.':
    'تبقى هذه الفحوصات موثقة لتوضيح الحدود الحالية. لا تدخل في الدرجة ولا تظهر كإخفاقات في نتيجة اختبار فردي.',
  'How the displayed score should be read': 'كيفية قراءة الدرجة المعروضة',
  'The displayed score summarizes only verified, applicable checks completed for the uploaded exam. Checks marked Not Verified or Not Applicable remain visible in the result but do not lower the score. Planned platform capabilities are also excluded.':
    'تلخص الدرجة المعروضة الفحوصات المتحقق منها والمنطبقة والمكتملة للاختبار المرفوع فقط. تظل الفحوصات غير المتحقق منها أو غير المنطبقة ظاهرة، لكنها لا تخفض الدرجة، كما تُستبعد القدرات المخطط لها.',
  'Enter the exam information, upload both PDFs, then review and start.':
    'أدخل معلومات الاختبار وارفع ملفي PDF ثم راجع وابدأ.',
  'Page not found': 'الصفحة غير موجودة',
  'This application route does not exist.': 'مسار التطبيق هذا غير موجود.',
  'Return to dashboard': 'العودة إلى لوحة التحكم',
  'Development reset link': 'رابط إعادة التعيين للتطوير',
  'choose a new password': 'اختر كلمة مرور جديدة',
  'Could not sign in': 'تعذر تسجيل الدخول',
  'Signing in…': 'جارٍ تسجيل الدخول…',
  'Passwords do not match.': 'كلمتا المرور غير متطابقتين.',
  'Each faculty member receives a private dashboard and analysis history.':
    'يحصل كل عضو هيئة تدريس على لوحة تحكم خاصة وسجل تحليل.',
  optional: 'اختياري',
  'Use at least 12 characters with at least one letter and one number.':
    'استخدم 12 محرفًا على الأقل تتضمن حرفًا واحدًا ورقمًا واحدًا على الأقل.',
  'Invalid reset link': 'رابط إعادة التعيين غير صالح',
  'Could not reset password': 'تعذر إعادة تعيين كلمة المرور',
  'The link is single-use and expires after the configured reset period.':
    'يُستخدم الرابط مرة واحدة وتنتهي صلاحيته بعد المدة المحددة.',
  'Request a new password reset link before continuing.':
    'اطلب رابطًا جديدًا لإعادة تعيين كلمة المرور قبل المتابعة.',
  'Use at least 12 characters with a letter and a number.':
    'استخدم 12 محرفًا على الأقل تتضمن حرفًا ورقمًا.',
  'Request a new reset link': 'طلب رابط إعادة تعيين جديد',
  'Department': 'القسم',
  'Term is required.': 'الفصل الدراسي مطلوب.',
  'Course code is required.': 'رمز المقرر مطلوب.',
  'Course name is required.': 'اسم المقرر مطلوب.',
  'Select Midterm or Final.': 'اختر اختبارًا نصفيًا أو نهائيًا.',
  'Show original text': 'عرض النص الأصلي',
  'Original source text': 'النص المصدري الأصلي',
  'Translated presentation': 'العرض المترجم',
  'Audit details': 'تفاصيل التدقيق',
  'Technical provenance': 'بيانات التتبع التقنية',
  'Interface language': 'لغة الواجهة',
  Arabic: 'العربية',
  English: 'الإنجليزية',
  'Start a new analysis': 'بدء تحليل جديد',
  'What We Evaluate': 'نطاق التقييم',
  'Declared total': 'المجموع المعلن',
  Instructions: 'التعليمات',
  'CLO citation': 'مرجع ناتج التعلم',
  'Topic citation': 'مرجع الموضوع',
  'Assessment record': 'سجل التقييم',
  'Missing section': 'قسم مفقود',
  'Question-to-CLO mapping': 'ربط الأسئلة بنواتج التعلم',
  'Relates exam questions to documented course learning outcomes using confirmed evidence.':
    'يربط أسئلة الاختبار بنواتج تعلم المقرر الموثقة باستخدام أدلة مؤكدة.',
  'CLO relevance': 'صلة السؤال بناتج التعلم',
  'Checks whether question content is relevant to the confirmed CLO relationship.':
    'يتحقق من صلة محتوى السؤال بناتج التعلم المؤكد.',
  'Assessment-method consistency': 'اتساق طريقة التقييم',
  'Checks consistency with the assessment methods documented in TP-153.':
    'يتحقق من الاتساق مع طرق التقييم الموثقة في TP-153.',
  'Question-format suitability': 'ملاءمة صيغة السؤال',
  'Reviews whether the question format is suitable for the intended response.':
    'يراجع مدى ملاءمة صيغة السؤال للاستجابة المطلوبة.',
  'Applicable CLO coverage': 'تغطية نواتج التعلم المنطبقة',
  'Summarizes which documented applicable CLOs are covered by the exam.':
    'يلخص نواتج التعلم الموثقة والمنطبقة التي يغطيها الاختبار.',
  'Question-to-topic alignment': 'مواءمة الأسئلة مع الموضوعات',
  'Relates questions to documented course topics when usable topic evidence is available.':
    'يربط الأسئلة بموضوعات المقرر الموثقة عند توفر أدلة موضوعات صالحة للاستخدام.',
  'Out-of-scope content': 'المحتوى خارج النطاق',
  'Flags question content that is not supported by the confirmed course evidence.':
    'يحدد محتوى السؤال الذي لا تدعمه أدلة المقرر المؤكدة.',
  'Applicable topic coverage': 'تغطية الموضوعات المنطبقة',
  'Summarizes coverage of documented topics designated for the exam.':
    'يلخص تغطية الموضوعات الموثقة والمحددة للاختبار.',
  'Clear task statement': 'وضوح المهمة المطلوبة',
  'Reviews whether the required task is stated clearly.':
    'يراجع ما إذا كانت المهمة المطلوبة مصاغة بوضوح.',
  'Unambiguous wording': 'صياغة غير ملتبسة',
  'Reviews question wording for avoidable ambiguity.':
    'يراجع صياغة السؤال للكشف عن الغموض الممكن تجنبه.',
  'Complete question information': 'اكتمال معلومات السؤال',
  'Checks whether the question contains the information needed to respond.':
    'يتحقق من احتواء السؤال على المعلومات اللازمة للإجابة.',
  'Correct total marks': 'صحة مجموع الدرجات',
  'Checks deterministic marks arithmetic when reliable marks evidence is available.':
    'يتحقق حسابيًا من مجموع الدرجات عند توفر أدلة موثوقة.',
  'Consistent numbering': 'اتساق الترقيم',
  'Checks the extracted question-numbering structure for consistency.':
    'يتحقق من اتساق بنية ترقيم الأسئلة المستخرجة.',
  'Complete instructions': 'اكتمال التعليمات',
  'Reviews whether required exam or question instructions are complete.':
    'يراجع اكتمال تعليمات الاختبار أو السؤال المطلوبة.',
  'CLO coverage distribution': 'توزيع تغطية نواتج التعلم',
  'The platform can evaluate this check when zero or one CLO is applicable. Cases with two or more applicable CLOs require an approved concentration method before distribution can be judged.':
    'يمكن تقييم هذا الفحص عند انطباق ناتج تعلم واحد أو عدم انطباق أي ناتج. أما انطباق ناتجين أو أكثر فيتطلب طريقة تركيز معتمدة قبل الحكم على التوزيع.',
  'Referenced material availability': 'توفر المواد المشار إليها',
  'Planned structured extraction of referenced figures, tables, code, and attachments.':
    'استخراج منظم مخطط له للأشكال والجداول والمقاطع البرمجية والمرفقات المشار إليها.',
  'Supporting material legibility': 'وضوح المواد المساندة',
  'Requires an approved visual-quality method and governed legibility thresholds.':
    'يتطلب طريقة معتمدة للجودة البصرية وضوابط محكومة للوضوح.',
  'Supporting material association': 'ارتباط المواد المساندة',
  'Planned layout-aware linking between questions and the correct supporting material.':
    'ربط مخطط له يراعي التخطيط بين الأسئلة والمواد المساندة الصحيحة.',
  'Visible marks': 'وضوح الدرجات',
  'Requires an approved institutional policy defining where marks must be displayed.':
    'يتطلب سياسة مؤسسية معتمدة تحدد مواضع عرض الدرجات.',
  'Exam identification': 'بيانات تعريف الاختبار',
  'Requires a configurable institutional list of mandatory exam-identification fields.':
    'يتطلب قائمة مؤسسية قابلة للضبط لحقول تعريف الاختبار الإلزامية.',
  'Resolvable cross-references': 'إحالات مرجعية قابلة للتحديد',
  'Planned layout-aware checking of references such as figures, tables, and other questions.':
    'فحص مخطط له يراعي التخطيط لإحالات مثل الأشكال والجداول والأسئلة الأخرى.',
  'Password reset instructions were requested. Check your email if an account exists.':
    'تم طلب تعليمات إعادة تعيين كلمة المرور. تحقق من بريدك الإلكتروني إذا كان الحساب موجودًا.',
  'Analysis not found.': 'التحليل غير موجود.',
  'Report not found.': 'التقرير غير موجود.',
  'This analysis has already been started.': 'بدأ هذا التحليل بالفعل.',
  'Only a failed analysis can be retried.': 'يمكن إعادة محاولة التحليل الفاشل فقط.',
  'This failure does not have a safe retry boundary.':
    'لا تتوفر نقطة آمنة لإعادة محاولة هذا الإخفاق.',
  'The original examination and TP-153 files are required before retrying.':
    'يلزم توفر ملفي الاختبار وTP-153 الأصليين قبل إعادة المحاولة.',
  'The original uploaded files are unavailable. Upload them in a new analysis.':
    'الملفات الأصلية المرفوعة غير متاحة. ارفعها ضمن تحليل جديد.',
  'The confirmed extraction revision required for retry is unavailable.':
    'نسخة الاستخراج المؤكدة المطلوبة لإعادة المحاولة غير متاحة.',
  'A retry or another processing action has already started.':
    'بدأت بالفعل إعادة محاولة أو عملية معالجة أخرى.',
  'A report can only be generated for a completed analysis.':
    'يمكن إنشاء تقرير لتحليل مكتمل فقط.',
  'An account with this email already exists.':
    'يوجد حساب مسجل بهذا البريد الإلكتروني.',
  'Invalid email or password.': 'البريد الإلكتروني أو كلمة المرور غير صحيحين.',
  'This password reset link is invalid or has expired.':
    'رابط إعادة تعيين كلمة المرور غير صالح أو منتهي الصلاحية.',
  'Materials & References': 'المواد والإحالات',
  'Supporting Materials & References': 'المواد المساندة والإحالات المرجعية',
  'Supporting materials': 'المواد المساندة',
  'Linked supporting context': 'السياق المساند المرتبط',
  'Linked Supporting Context': 'السياق المساند المرتبط',
  'View details in Linked Supporting Context': 'عرض التفاصيل في صفحة السياق المساند المرتبط',
  'Review the confirmed visual, table, or code context linked to each question.':
    'راجع الرسم أو الجدول أو الكود المؤكد والمرتبط بكل سؤال.',
  'Confirmed question-to-context links': 'ارتباطات الأسئلة بالسياق المؤكدة',
  'Supporting context': 'السياق المساند',
  'Extracted description': 'الوصف المستخرج',
  'No confirmed question-to-context links were identified.':
    'لم يتم تحديد ارتباطات مؤكدة بين الأسئلة والسياق المساند.',
  'Missing questions can still be added from the PDF inside the review screen.':
    'يمكن إضافة الأسئلة المفقودة من ملف PDF داخل شاشة المراجعة.',
  'Technical diagnostics': 'التشخيصات التقنية',
  'Possible missing question content': 'محتوى محتمل لسؤال مفقود',
  '{assessed} assessed questions + {containers} structural containers':
    '{assessed} سؤالًا مقيمًا + {containers} أسئلة هيكلية',
  'Only high-confidence figures, tables, or code context explicitly needed by a question are shown. Confirm the linked question or exclude the item before continuing.':
    'تظهر فقط الأشكال أو الجداول أو مقاطع الشفرة عالية الثقة التي يحتاجها سؤال بشكل صريح. أكد السؤال المرتبط أو استبعد العنصر قبل المتابعة.',
  'No question-linked supporting context was detected.':
    'لم يُكتشف سياق مساند مرتبط بسؤال.',
  'Labels and captions': 'التسميات والعناوين التوضيحية',
  'Explicit references': 'الإحالات الصريحة',
  'Association candidates': 'مرشحو الارتباط',
  'Loading supporting-material evidence': 'جارٍ تحميل أدلة المواد المساندة',
  'Could not load supporting-material evidence': 'تعذر تحميل أدلة المواد المساندة',
  'Could not load supporting-material evidence.': 'تعذر تحميل أدلة المواد المساندة.',
  'Retrieving figures, tables, code blocks, and explicit references…':
    'جارٍ استرجاع الأشكال والجداول ومقاطع الشفرة والإحالات الصريحة…',
  'No structured supporting material': 'لا توجد مواد مساندة منظمة',
  'No figures, tables, code blocks, or explicit references were extracted.':
    'لم تُستخرج أشكال أو جداول أو مقاطع شفرة أو إحالات صريحة.',
  'Exact labels and explicit references determine verified associations. Proximity is shown only as supporting audit evidence.':
    'تحدد التسميات المطابقة والإحالات الصريحة الارتباطات المتحقق منها، ويُعرض القرب بوصفه دليل تدقيق مساندًا فقط.',
  'Proximity candidates are retained for review and never verify an association by themselves.':
    'يُحتفظ بمرشحي القرب للمراجعة، ولا يثبتون الارتباط بمفردهم.',
  'Extraction method': 'طريقة الاستخراج',
  'Confidence': 'الثقة',
  'Target type': 'نوع الهدف',
  'Target label': 'تسمية الهدف',
  'Resolution': 'حالة التحديد',
  'Candidates': 'المرشحون',
  'Include reference': 'تضمين الإحالة',
  'Selected exact target': 'هدف مطابق محدد',
  'Review candidate': 'مرشح للمراجعة',
  Distance: 'المسافة',
  'Review revision': 'مراجعة بشرية',
  'Machine extraction': 'الاستخراج الآلي',
  'Target identifier': 'معرّف الهدف',
  'Checks whether explicitly referenced figures, tables, and code blocks resolve to a present, uniquely labelled item.':
    'يتحقق مما إذا كانت الأشكال والجداول ومقاطع الشفرة المشار إليها صراحةً تُحال إلى عنصر موجود ذي تسمية فريدة.',
  'Uses exact labels and explicit references to associate supporting material with its intended question; proximity alone never verifies an association.':
    'يستخدم التسميات المطابقة والإحالات الصريحة لربط المادة المساندة بالسؤال المقصود، ولا يكفي القرب وحده للتحقق من الارتباط.',
  'Checks whether explicit references resolve to one exact, identifiable item and retains ambiguous candidates for review.':
    'يتحقق من أن الإحالات الصريحة تُحال إلى عنصر واحد مطابق وقابل للتحديد، مع الاحتفاظ بالمرشحين الملتبسين للمراجعة.',
  'Original source content is preserved for audit.':
    'يُحفظ محتوى المصدر الأصلي لأغراض التدقيق.',
  'Original label or caption is preserved for audit.':
    'تُحفظ التسمية أو العبارة التوضيحية الأصلية لأغراض التدقيق.',
  'Original reference wording is preserved for audit.':
    'تُحفظ صياغة الإحالة الأصلية لأغراض التدقيق.',
  'Proximity is supporting evidence only.':
    'القرب دليل مساند فقط ولا يثبت الارتباط بمفرده.',
  'Multiple exact targets share this label.':
    'تشترك عدة أهداف مطابقة في هذه التسمية.',
  figure: 'شكل',
  table: 'جدول',
  'code block': 'مقطع شفرة',
  caption: 'عنوان توضيحي',
  label: 'تسمية',
  resolved: 'محدد بصورة فريدة',
  ambiguous: 'ملتبس',
  unresolved: 'غير محدد',
  exact_label: 'تسمية مطابقة',
  proximity_support: 'دليل قرب مساند',
  direct_text: 'نص مباشر',
  ocr: 'تعرّف ضوئي',
  'Top-level question': 'سؤال من المستوى الأعلى',
  'Extraction candidates': 'مرشحو الاستخراج',
  'Canonical proposed value': 'القيمة الأساسية المقترحة',
  'Source/provenance': 'المصدر وسجل المنشأ',
  'Local-only extraction': 'استخراج محلي فقط',
  'Unassigned visible candidates': 'مرشحات مرئية غير مرتبطة',
  'These candidates are retained for audit and require resolution before confirmation.':
    'تُحفظ هذه المرشحات للتدقيق وتتطلب المعالجة قبل التأكيد.',
  'Original question from PDF': 'السؤال الأصلي من ملف PDF',
  'This image is the source reference. The editable text below is only a proposed transcription.':
    'هذه الصورة هي المرجع الأصلي، أما النص القابل للتعديل أدناه فهو تفريغ مقترح فقط.',
  'Editable extracted data': 'بيانات الاستخراج القابلة للتعديل',
  'Correct the proposal only when it differs from the original image.':
    'صحح المقترح فقط عندما يختلف عن الصورة الأصلية.',
  'Review question': 'مراجعة السؤال',
  'Hide review details': 'إخفاء تفاصيل المراجعة',
  'Marks not detected': 'لم تُكتشف الدرجة',
  'Detected blanks': 'الفراغات المكتشفة',
  'No answer options were detected for this question.':
    'لم تُكتشف خيارات إجابة لهذا السؤال.',
  'Blank details are optional review aids and are not a replacement for the original question image.':
    'تفاصيل الفراغات وسيلة مساعدة اختيارية ولا تستبدل صورة السؤال الأصلية.',
  'Advanced structure and extraction details': 'تفاصيل البنية والاستخراج المتقدمة',
  'Adjust question area': 'تعديل حدود السؤال',
  'Cancel area adjustment': 'إلغاء تعديل الحدود',
  'Drag over the complete original question, including its table, figure, or answer area.':
    'اسحب فوق السؤال الأصلي كاملًا، بما في ذلك الجدول أو الشكل أو مساحة الإجابة.',
  'The original question image is unavailable until a question area is selected.':
    'لا تتوفر صورة السؤال الأصلية حتى يتم تحديد منطقة السؤال.',
  'Loading original question image…': 'جارٍ تحميل صورة السؤال الأصلية…',
  'Could not render the original question image.': 'تعذر عرض صورة السؤال الأصلية.',
  'Not detected': 'غير مكتشف',
  'No questions were detected automatically': 'لم تُكتشف أسئلة تلقائيًا',
  'Use the original PDF to add each visible question region before analysis.':
    'استخدم ملف PDF الأصلي لإضافة منطقة كل سؤال ظاهر قبل بدء التحليل.',
  'No reliable questions were extracted automatically. Add the visible question regions from the original PDF, rerun extraction, or replace the exam file.':
    'لم تُستخرج أسئلة موثوقة تلقائيًا. أضف مناطق الأسئلة الظاهرة من ملف PDF الأصلي، أو أعد الاستخراج، أو استبدل ملف الاختبار.',
  'Human-assisted visual review': 'مراجعة بصرية بمساعدة النظام',
  'Add or correct question regions using the original PDF before saving.':
    'أضف الأسئلة المفقودة أو صحح حدودها بالاعتماد على ملف PDF الأصلي قبل الحفظ.',
  'Add missing question from PDF': 'إضافة سؤال مفقود من ملف PDF',
  'New question': 'سؤال جديد',
  'Split / add second part': 'تقسيم / إضافة جزء ثانٍ',
  'Merge with previous question': 'دمج مع السؤال السابق',
  'Remove added question': 'حذف السؤال المضاف',
  'Complete the added question': 'أكمل بيانات السؤال المضاف',
  'Select its complete region in the PDF, then enter the question text before saving.':
    'حدد منطقة السؤال كاملة في ملف PDF، ثم أدخل نص السؤال قبل الحفظ.',
  'Complete the added questions before saving': 'أكمل الأسئلة المضافة قبل الحفظ',
  'Each added question needs a question number, editable text, and a selected region from the original PDF.':
    'يحتاج كل سؤال مضاف إلى رقم ونص قابل للتعديل ومنطقة محددة من ملف PDF الأصلي.',
  'Complete every added question by selecting its PDF region and entering its number and text.':
    'أكمل كل سؤال مضاف بتحديد منطقته في ملف PDF وإدخال رقمه ونصه.',
  'A parent question with included child questions cannot be merged.':
    'لا يمكن دمج سؤال رئيسي ما دامت تحته أسئلة فرعية مضمنة.',
  'No previous included question is available on this page.':
    'لا يوجد سؤال سابق مضمن في هذه الصفحة يمكن الدمج معه.',
  'Question blanks': 'فراغات السؤال',
  'Include blank': 'تضمين الفراغ',
  'Blank source text': 'نص مصدر الفراغ',
  'Associated question': 'السؤال المرتبط',
  Unassigned: 'غير مرتبط',
  'Requires manual review': 'يتطلب مراجعة يدوية',
  'Analysis incomplete': 'التحليل غير مكتمل',
  'A quality score is hidden until confirmed question evidence is available.':
    'تم إخفاء درجة الجودة حتى تتوفر أدلة أسئلة مؤكدة.',
  'Checking confirmed question evidence': 'جارٍ التحقق من أدلة الأسئلة المؤكدة',
  'Academic results are shown only after confirmed questions are available.':
    'تظهر النتائج الأكاديمية فقط بعد توفر أسئلة مؤكدة.',
  'Confirmed question evidence could not be loaded, so academic results and the score are hidden.':
    'تعذر تحميل أدلة الأسئلة المؤكدة، لذلك تم إخفاء النتائج الأكاديمية والدرجة.',
  'No confirmed questions are available. Return to extraction review before relying on academic results.':
    'لا توجد أسئلة مؤكدة. ارجع إلى مراجعة الاستخراج قبل الاعتماد على النتائج الأكاديمية.',
  'How should questions be prepared?': 'كيف تريد تجهيز أسئلة الاختبار؟',
  'Choose the safest workflow for the uploaded exam. The academic analysis starts only after you confirm the questions.':
    'اختر المسار الأنسب للاختبار المرفوع. لا يبدأ التحليل الأكاديمي إلا بعد تأكيد الأسئلة.',
  'Assisted extraction from PDF': 'استخراج مساعد من ملف PDF',
  'Best for clear digital exams. The platform proposes questions and you correct every boundary and transcription.':
    'مناسب للاختبارات الرقمية الواضحة. تقترح المنصة الأسئلة، ثم تراجع حدود كل سؤال ونصه.',
  'Structured question template': 'قالب أسئلة منظم',
  'Most reliable. Import a controlled CSV in Extraction Review, then compare it with the original PDF.':
    'المسار الأكثر موثوقية. استورد ملف CSV منظمًا في مراجعة الاستخراج، ثم قارنه بملف PDF الأصلي.',
  'Recommended for dependable results': 'موصى به للنتائج الموثوقة',
  'Manual visual review from PDF': 'مراجعة بصرية يدوية من ملف PDF',
  'Use for irregular layouts. Add each visible question by selecting its region in the original PDF.':
    'استخدمه للتنسيقات غير المنتظمة. أضف كل سؤال ظاهر بتحديد منطقته في ملف PDF الأصلي.',
  'No structured questions have been imported': 'لم تُستورد أسئلة منظمة',
  'No manual questions have been added': 'لم تُضف أسئلة يدويًا',
  'Import the completed CSV template above, then review every question against the original PDF.':
    'استورد قالب CSV المكتمل أعلاه، ثم راجع كل سؤال مقابل ملف PDF الأصلي.',
  'Structured question review': 'مراجعة الأسئلة المنظمة',
  'Compare every imported row with the original PDF. Marks may remain empty when they are not visibly written.':
    'قارن كل صف مستورد بملف PDF الأصلي. يمكن ترك الدرجة فارغة عندما لا تكون مكتوبة بوضوح.',
  'These source lines are retained for audit. Review them only when they contain missing question content.':
    'تُحفظ هذه الأسطر للتدقيق. راجعها فقط عندما تحتوي جزءًا مفقودًا من سؤال.',
  'The structured template identifies the source page but does not invent a precise PDF region.':
    'يحدد القالب المنظم صفحة المصدر دون اختراع منطقة دقيقة داخل ملف PDF.',
  'Show source page': 'عرض صفحة المصدر',
  'Structured question template imported. Review every question before saving.':
    'تم استيراد قالب الأسئلة المنظم. راجع كل سؤال قبل الحفظ.',
  'Could not import the structured question template.': 'تعذر استيراد قالب الأسئلة المنظم.',
  'Import confirmed question text, type, visible marks, page number, and multiple-choice options. Empty marks remain unknown and are never invented.':
    'استورد نص السؤال المؤكد ونوعه والدرجة الظاهرة ورقم الصفحة وخيارات الاختيار من متعدد. تبقى الدرجة الفارغة غير معروفة ولا تُخترع.',
  'Download CSV template': 'تنزيل قالب CSV',
  'Import completed CSV': 'استيراد ملف CSV المكتمل',
  'Manual visual question preparation': 'تجهيز الأسئلة بالمراجعة البصرية اليدوية',
  'No automatic questions are trusted in this mode. Select a page region, add the visible question, enter only the text shown in the PDF, and save the revision.':
    'لا تُعتمد أسئلة تلقائية في هذا المسار. حدد منطقة في الصفحة، وأضف السؤال الظاهر، وأدخل فقط النص الموجود في PDF، ثم احفظ المراجعة.',
  'Assisted PDF extraction': 'الاستخراج المساعد من PDF',
  'Automatic extraction is a proposal only. Correct incomplete text and question regions before confirmation.':
    'الاستخراج التلقائي مجرد اقتراح. صحح النصوص الناقصة وحدود الأسئلة قبل التأكيد.',
  'Import the question template to continue': 'استورد قالب الأسئلة للمتابعة',
  'Download the CSV template, complete one row per confirmed question, and import it here.':
    'نزّل قالب CSV، وأكمل صفًا لكل سؤال مؤكد، ثم استورده هنا.',
  'Complete every imported question by entering its number and text.':
    'أكمل كل سؤال مستورد بإدخال رقمه ونصه.',
  'Each imported question needs a question number and editable source-faithful text.':
    'يحتاج كل سؤال مستورد إلى رقم ونص قابل للتعديل مطابق للمصدر.',
  'The CSV contains an unclosed quoted field.': 'يحتوي ملف CSV على حقل مقتبس غير مغلق.',
  'Marks must be empty or a non-negative number.': 'يجب أن تكون الدرجة فارغة أو رقمًا غير سالب.',
  'Page number must be a positive whole number.': 'يجب أن يكون رقم الصفحة عددًا صحيحًا موجبًا.',
  'The template must contain a header and at least one question row.':
    'يجب أن يحتوي القالب على ترويسة وصف واحد للأسئلة على الأقل.',
  'Question number is required.': 'رقم السؤال مطلوب.',
  'Question text is required.': 'نص السؤال مطلوب.',
  'Question type must be multiple_choice, true_false, fill_in_blank, short_answer, or essay.':
    'يجب أن يكون نوع السؤال اختيارًا من متعدد أو صح وخطأ أو فراغًا أو إجابة قصيرة أو مقاليًا.',
  'A multiple-choice question needs at least two answer options.':
    'يحتاج سؤال الاختيار من متعدد إلى خيارين على الأقل.',
  'Answer-option columns must be empty unless the question type is multiple_choice.':
    'يجب أن تبقى أعمدة الخيارات فارغة ما لم يكن السؤال اختيارًا من متعدد.',
  'Question numbers must be unique in the structured template:':
    'يجب ألا تتكرر أرقام الأسئلة في القالب المنظم:',
  'Missing required columns': 'الأعمدة المطلوبة مفقودة',
  'Question numbers must be unique in the structured template':
    'يجب ألا تتكرر أرقام الأسئلة في القالب المنظم',
  'A referenced parent question was not found in the template.':
    'لم يتم العثور على السؤال الرئيسي المشار إليه داخل القالب.',
  'Best for clear digital exams. The platform proposes questions and you correct only the items that need attention.':
    'مناسب للاختبارات الرقمية الواضحة. تقترح المنصة الأسئلة، وتصحح فقط العناصر التي تحتاج إلى مراجعة.',
  'Recommended starting point': 'نقطة البداية الموصى بها',
  'Paste or import question list': 'لصق أو استيراد قائمة الأسئلة',
  'Paste questions copied from Word or import a simple CSV. Only number, text, and visible marks are required.':
    'الصق الأسئلة المنسوخة من Word أو استورد ملف CSV بسيطًا. المطلوب فقط رقم السؤال ونصه والدرجة الظاهرة.',
  'Add questions manually from PDF': 'إضافة أسئلة يدويًا من ملف PDF',
  'Use only when automatic extraction misses a question or the layout is highly irregular.':
    'استخدمه فقط عندما يفوّت الاستخراج التلقائي سؤالًا أو يكون التنسيق غير منتظم بدرجة كبيرة.',
  'Paste questions copied from Word or PDF, or import the simple CSV. Only question number, text, and visible marks are required. Type and options are optional.':
    'الصق الأسئلة المنسوخة من Word أو PDF، أو استورد ملف CSV البسيط. المطلوب فقط رقم السؤال ونصه والدرجة الظاهرة، أما النوع والخيارات فاختيارية.',
  'Paste questions': 'لصق الأسئلة',
  'Paste numbered questions here. Keep answer options on lines beginning with A, B, C, or D.':
    'الصق الأسئلة المرقمة هنا. اجعل خيارات الإجابة في أسطر تبدأ بـ A أو B أو C أو D.',
  'Import pasted questions': 'استيراد الأسئلة الملصقة',
  'Download simple CSV': 'تنزيل ملف CSV بسيط',
  'Import CSV': 'استيراد CSV',
  'Pasted questions imported. Review every question before saving.':
    'تم استيراد الأسئلة الملصقة. راجع كل سؤال قبل الحفظ.',
  'Could not import the pasted questions.': 'تعذر استيراد الأسئلة الملصقة.',
  'Paste at least one question before importing.': 'الصق سؤالًا واحدًا على الأقل قبل الاستيراد.',
  'No pasted or imported questions are available': 'لا توجد أسئلة ملصقة أو مستوردة',
  'Paste questions or import the simple CSV above, then review them against the original PDF.':
    'الصق الأسئلة أو استورد ملف CSV البسيط أعلاه، ثم راجعها مقابل ملف PDF الأصلي.',
  'Paste or import questions to continue': 'الصق الأسئلة أو استوردها للمتابعة',
  'Paste questions copied from Word or import the simple CSV to continue.':
    'الصق الأسئلة المنسوخة من Word أو استورد ملف CSV البسيط للمتابعة.',
  'Use the PDF as the source reference': 'استخدم ملف PDF كمرجع أصلي',
  'The original page is shown on the left. Use Show in PDF to verify the complete question and adjust the highlighted region only when needed.':
    'تظهر الصفحة الأصلية في الجهة اليسرى. استخدم زر العرض في PDF للتحقق من السؤال كاملًا، وعدّل منطقة التحديد عند الحاجة فقط.',
  'Correct the proposal only when it differs from the original PDF shown on the left.':
    'صحح الاقتراح فقط عندما يختلف عن ملف PDF الأصلي الظاهر في الجهة اليسرى.',
  Row: 'الصف',
  local_only: 'محلي فقط',
  local: 'محلي',
  unknown: 'غير معروف',
  fresh_gemini: 'Gemini جديد',
  cache: 'نسخة Gemini مخزنة مؤقتًا',
  targeted_ocr: 'تعرف ضوئي موجه',
  ...OCR_ARABIC_MESSAGES,
  ...BATCH5_ARABIC_MESSAGES,
  ...BATCH5_REFINEMENT_ARABIC_MESSAGES,
  ...PILOT_REFINEMENT_ARABIC_MESSAGES,
  ...METHODOLOGY_ARABIC_MESSAGES,
  ...REPORTS_ARABIC_MESSAGES,
  'The rendered page image could not be displayed. Use the PDF fallback below or try again.': 'تعذّر عرض صورة الصفحة. استخدمي نسخة PDF الاحتياطية أدناه أو أعيدي المحاولة.',
  'The original PDF remains available while the page image is retried.': 'يبقى ملف PDF الأصلي متاحًا أثناء إعادة محاولة عرض صورة الصفحة.',
  'Manual visual review required': 'تتطلب مراجعة بصرية يدوية',
  'CLOs represented': 'نواتج التعلم الممثلة',
  'Topics represented': 'موضوعات المقرر الممثلة',
  'This is an advisory estimate of exam quality based on the criteria that could be verified. It is not the exam mark or a student pass rate.':
    'هذه نسبة تقديرية لجودة الاختبار بناءً على المعايير التي أمكن التحقق منها، وليست درجة للاختبار أو نسبة لنجاح الطلاب.',
  'No individual mark specified; section total': 'لم تُحدد درجة فردية؛ مجموع القسم',
  'Validating files': 'التحقق من الملفات',
  'Extracting questions': 'استخراج الأسئلة',
  'Reviewing extraction': 'مراجعة الاستخراج',
  'Preparing evidence': 'تجهيز الأدلة',
  'Retrieving evaluation knowledge': 'استرجاع معرفة التقييم',
  'Applying evaluation criteria': 'تطبيق معايير التقييم',
  'Generating results': 'إنشاء النتائج',
  'Checking the uploaded Exam and Course Specification files.':
    'يجري التحقق من ملفي الاختبار وتوصيف المقرر المرفوعين.',
  'Reading questions, marks, and visible exam structure.':
    'تجري قراءة الأسئلة والدرجات والبنية الظاهرة للاختبار.',
  'Preparing the extracted questions for faculty review.':
    'يجري تجهيز الأسئلة المستخرجة لمراجعة عضو هيئة التدريس.',
  'Preparing the confirmed extraction as analysis evidence.':
    'يجري تجهيز الاستخراج المؤكد بوصفه دليلًا للتحليل.',
  'Retrieving the validated evaluation knowledge.':
    'يجري استرجاع معرفة التقييم المتحقق منها.',
  'Linking questions with evaluation criteria.':
    'يجري ربط الأسئلة بمعايير التقييم.',
  'Generating the findings and results.': 'يجري إنشاء النتائج والمخرجات.',
  'Checking uploaded files': 'التحقق من الملفات المرفوعة',
  'Reading the examination': 'قراءة الاختبار',
  'Reading the Course Specification': 'قراءة توصيف المقرر',
  'Preparing confirmed evidence': 'إعداد الأدلة المؤكدة',
  'Preparing reference knowledge': 'إعداد المعرفة المرجعية',
  'Evaluating exam quality': 'تقييم جودة الاختبار',
  'Finalizing results': 'إنهاء النتائج',
  'The uploaded Exam and Course Specification are being checked.':
    'يجري التحقق من ملف الاختبار وتوصيف المقرر المرفوعين.',
  'The examination questions, marks, and visible structure are being read.':
    'تجري قراءة أسئلة الاختبار ودرجاته وبنيته الظاهرة.',
  'Course outcomes, topics, and assessment information are being read.':
    'تجري قراءة نواتج المقرر وموضوعاته ومعلومات التقييم.',
  'Your confirmed extraction is being prepared for analysis.':
    'يجري إعداد الاستخراج الذي أكدته للتحليل.',
  'The controlled reference knowledge is being prepared.':
    'يجري إعداد المعرفة المرجعية المنضبطة.',
  'The analyzer is applying the available evidence-based quality checks.':
    'يطبق المحلل فحوصات الجودة المتاحة القائمة على الأدلة.',
  'The findings and results are being finalized.': 'يجري إنهاء النتائج والمخرجات.',
  'Current stage': 'المرحلة الحالية',
  'Elapsed time': 'الوقت المنقضي',
  'Progress check timed out': 'انتهت مهلة التحقق من التقدم',
  'The analysis is still running. Progress will be checked again automatically.':
    'لا يزال التحليل جاريًا، وسيُتحقق من التقدم مرة أخرى تلقائيًا.',
  'Stage needing attention': 'المرحلة التي تحتاج إلى معالجة',
}
