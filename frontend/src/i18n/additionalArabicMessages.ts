import { BATCH5_ARABIC_MESSAGES } from './batch5ArabicMessages'
import { BATCH5_REFINEMENT_ARABIC_MESSAGES } from './batch5RefinementArabicMessages'
import { METHODOLOGY_ARABIC_MESSAGES } from './methodologyArabicMessages'
import { PILOT_REFINEMENT_ARABIC_MESSAGES } from './pilotRefinementArabicMessages'
import { REPORTS_ARABIC_MESSAGES } from './reportsArabicMessages'

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
  'No verified checks were available': 'لا توجد فحوصات متحقق منها',
  'Based on 1 verified check': 'استنادًا إلى فحص واحد متحقق منه',
  'Based on {count} verified checks': 'استنادًا إلى {count} فحوصات متحقق منها',
  Course: 'المقرر',
  'Exam type': 'نوع الاختبار',
  Created: 'تاريخ الإنشاء',
  Relationship: 'العلاقة',
  'Linked reanalysis': 'إعادة تحليل مرتبطة',
  Original: 'أصلي',
  'Open analysis': 'فتح التحليل',
  'Analysis summary': 'ملخص التحليلات',
  'Total analyses': 'إجمالي التحليلات',
  'Completed analyses': 'التحليلات المكتملة',
  'Linked reanalyses': 'إعادات التحليل المرتبطة',
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
  'Could not create the reanalysis.': 'تعذر إنشاء إعادة التحليل.',
  'Analyze a revised exam': 'تحليل نسخة منقحة من الاختبار',
  'Create a reanalysis linked to analysis': 'إنشاء إعادة تحليل مرتبطة بالتحليل',
  'This analysis and its reports remain unchanged.': 'سيبقى هذا التحليل وتقاريره دون تغيير.',
  'Reuse the previous TP-153 (uncheck to upload a new one)':
    'إعادة استخدام TP-153 السابق (أزل التحديد لرفع ملف جديد)',
  'Creating…': 'جارٍ الإنشاء…',
  'Create Reanalysis': 'إنشاء إعادة تحليل',
  'Could not create reanalysis': 'تعذر إنشاء إعادة التحليل',
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
  'Linked reanalysis of': 'إعادة تحليل مرتبطة بـ',
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
  'Only a completed analysis can be reanalyzed.':
    'يمكن إنشاء إعادة تحليل لتحليل مكتمل فقط.',
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
  ...BATCH5_ARABIC_MESSAGES,
  ...BATCH5_REFINEMENT_ARABIC_MESSAGES,
  ...PILOT_REFINEMENT_ARABIC_MESSAGES,
  ...METHODOLOGY_ARABIC_MESSAGES,
  ...REPORTS_ARABIC_MESSAGES,
}
