import type {
  AcademicStatus,
  FindingResponse,
  Locale,
  RecommendationResponse,
} from '../types/api'

const REQUIREMENT_NAMES_AR: Readonly<Record<string, string>> = {
  REQ001: 'ربط السؤال بناتج التعلم للمقرر',
  REQ002: 'صلة السؤال بناتج التعلم',
  REQ003: 'اتساق أسلوب التقييم',
  REQ004: 'ملاءمة صيغة السؤال',
  REQ005: 'تغطية نواتج التعلم المنطبقة',
  REQ006: 'توزيع تغطية نواتج التعلم',
  REQ007: 'مواءمة السؤال مع موضوعات المقرر',
  REQ008: 'المحتوى خارج النطاق',
  REQ009: 'تغطية موضوعات المقرر المنطبقة',
  REQ010: 'قابلية تتبع نتيجة التقييم',
  REQ011: 'وضوح المهمة المطلوبة',
  REQ012: 'صياغة غير ملتبسة',
  REQ013: 'اكتمال معلومات السؤال',
  REQ014: 'توفر المواد المشار إليها',
  REQ015: 'وضوح المواد المساندة',
  REQ016: 'ارتباط المواد المساندة',
  REQ017: 'وضوح الدرجات',
  REQ018: 'صحة مجموع الدرجات',
  REQ019: 'اتساق الترقيم',
  REQ020: 'بيانات تعريف الاختبار',
  REQ021: 'اكتمال التعليمات',
  REQ022: 'إمكانية تحديد الإحالات المرجعية',
  REQ023: 'قابلية قراءة ملف الاختبار',
  REQ024: 'صلاحية بيانات نواتج التعلم',
  REQ025: 'صلاحية بيانات موضوعات المقرر',
  REQ026: 'صلاحية بيانات التقييم',
  REQ027: 'توصية قابلة للتنفيذ',
  REQ028: 'استنتاجات على مستوى الاختبار',
  REQ029: 'حالة واحدة لكل قاعدة',
  REQ030: 'تفسير مستند إلى الأدلة',
}

const DIMENSIONS_AR: Readonly<Record<string, string>> = {
  'CLO Alignment': 'مواءمة نواتج التعلم',
  'Assessment Alignment': 'مواءمة التقييم',
  'CLO Coverage': 'تغطية نواتج التعلم',
  'Topic Alignment': 'مواءمة موضوعات المقرر',
  'Topic Coverage': 'تغطية موضوعات المقرر',
  Traceability: 'قابلية التتبع',
  'Question Clarity': 'وضوح السؤال',
  'Question Completeness': 'اكتمال السؤال',
  'Supporting Material': 'المواد المساندة',
  'Marks and Totals': 'الدرجات والمجاميع',
  'Numbering and Structure': 'الترقيم والبنية',
  'Exam Information': 'بيانات الاختبار',
  'Exam Instructions': 'تعليمات الاختبار',
  'Cross-References': 'الإحالات المرجعية',
  'Input Quality': 'جودة المدخلات',
  Recommendations: 'التوصيات',
  'Scope Governance': 'حوكمة النطاق',
  'Status Governance': 'حوكمة الحالات',
  Explainability: 'قابلية التفسير',
}

const META_AR: Readonly<Record<string, string>> = {
  'Derived Exam Requirement': 'متطلب اختبار مستنتج',
  'System Requirement': 'متطلب تشغيلي',
  Derived: 'مستنتج',
  'System Defined': 'محدد تشغيليًا',
  Faculty: 'عضو هيئة التدريس',
  'Faculty and Course Coordinator': 'عضو هيئة التدريس ومنسق المقرر',
  'Faculty or Course Coordinator': 'عضو هيئة التدريس أو منسق المقرر',
  'Course Coordinator': 'منسق المقرر',
  'System Owner': 'مسؤول النظام',
  'System Owner and Quality Officer': 'مسؤول النظام ومسؤول الجودة',
  Corrective: 'تصحيحية',
  Advisory: 'استرشادية',
  'System Correction': 'تصحيح تشغيلي',
  'Input Correction': 'تصحيح المدخلات',
  'Input Request': 'طلب مدخلات',
  Governance: 'حوكمة',
}

const RECOMMENDATIONS_AR: Readonly<Record<string, readonly [string, string]>> = {
  REC001: ['اربط السؤال بناتج تعلم', 'راجع السؤال واربطه بناتج تعلم واحد على الأقل تدعمه أدلة المقرر.'],
  REC002: ['عزّز صلة السؤال بناتج التعلم', 'عدّل السؤال بحيث تقدم الإجابة المتوقعة دليلًا أوضح على ناتج التعلم المرتبط.'],
  REC003: ['وائم الاختبار مع توصيف المقرر', 'راجع أسلوب أو نشاط التقييم الموثق وحقق الاتساق بين تصميم الاختبار وتوصيف المقرر.'],
  REC004: ['استخدم صيغة سؤال ملائمة', 'عدّل صيغة الاستجابة حتى يتمكن الطالب من إظهار ناتج التعلم المقصود.'],
  REC005: ['غطِّ ناتج التعلم غير المغطى', 'أضف سؤالًا مناسبًا يدعم ناتج التعلم المنطبق أو وثّق تقييمه في موضع آخر.'],
  REC006: ['حسّن توزيع تغطية نواتج التعلم', 'راجع توزيع الأسئلة أو الدرجات على نواتج التعلم المنطبقة وقلل التركّز غير المقصود.'],
  REC007: ['وائم السؤال مع موضوعات المقرر', 'عدّل الجزء غير المدعوم من السؤال أو أزله ليتوافق مع موضوعات المقرر الموثقة.'],
  REC008: ['أزل المحتوى المقيم خارج النطاق', 'عدّل المحتوى المقيم جوهريًا خارج موضوعات المقرر أو حدّث توصيف المقرر رسميًا.'],
  REC009: ['غطِّ موضوعات الاختبار المقصودة', 'أضف أسئلة مناسبة للموضوعات المقصودة التي لا تحظى بتغطية كافية.'],
  REC010: ['أكمل مسار الأدلة', 'أضف المستند المصدر والصفحة والسؤال أو السؤال الفرعي وناتج التعلم أو الموضوع المرتبط.'],
  REC011: ['وضّح المهمة المطلوبة', 'حدّد بدقة ما يجب على الطالب فعله أو إنتاجه.'],
  REC012: ['أزل الالتباس المؤثر', 'وضّح المصطلحات والشروط والإحالات ونطاق الإجابة المتوقعة.'],
  REC013: ['أكمل معلومات السؤال', 'أضف البيانات أو الشروط أو الافتراضات أو السياق اللازم للإجابة.'],
  REC014: ['وفّر المادة المساندة المطلوبة', 'أدرج الشكل أو الجدول أو الشفرة أو مجموعة البيانات أو المرفق واربطه بالسؤال المعني.'],
  REC015: ['حسّن وضوح المادة المساندة', 'حسّن الدقة أو التباين أو الحجم أو الاقتصاص أو قابلية قراءة المادة المساندة.'],
  REC016: ['اربط العنصر المساند بوضوح', 'انقل المادة المساندة أو سمّها أو أشر إليها بحيث يتضح سؤالها المقصود.'],
  REC017: ['اعرض الدرجات بوضوح', 'أضف الدرجات أو وضّحها على مستوى السؤال أو السؤال الفرعي أو القسم.'],
  REC018: ['صحّح مجموع الدرجات', 'أعد حساب الدرجات واجعل المجموع المعلن مطابقًا لمجموع جميع العناصر المحتسبة.'],
  REC019: ['أصلح ترقيم الأسئلة', 'صحّح الترقيم المكرر أو المفقود أو غير المتسق للأسئلة والأسئلة الفرعية.'],
  REC020: ['أكمل بيانات تعريف الاختبار', 'أضف بيانات المقرر والاختبار والفصل والتاريخ والمدة ومجموع الدرجات المطلوبة مؤسسيًا.'],
  REC021: ['أكمل التعليمات', 'أضف التعليمات اللازمة بشأن الإجابات أو المصادر أو الأدوات أو القيود.'],
  REC022: ['حدّد الإحالة المرجعية', 'استبدل الإحالات المبهمة بمعرّف محدد لشكل أو جدول أو سؤال أو صفحة.'],
  REC023: ['وفّر نسخة مقروءة من الاختبار', 'ارفع ملف اختبار كاملًا وأكثر وضوحًا قبل إعادة التحليل.'],
  REC024: ['صحّح بيانات نواتج التعلم', 'أكمل عبارات نواتج التعلم وصحّح الرموز المكررة أو غير الصالحة عبر الإجراء الرسمي لتوصيف المقرر.'],
  REC025: ['وفّر موضوعات مقرر صالحة للاستخدام', 'أكمل قسم الموضوعات في توصيف المقرر بموضوعات واضحة ومتميزة.'],
  REC026: ['أكمل بيانات التقييم', 'وفّر أساليب أو أنشطة التقييم المطلوبة بصورة مقروءة.'],
  REC027: ['اجعل التوصية قابلة للتنفيذ', 'حدّد المشكلة والعنصر والإجراء التصحيحي ورابط الدليل بدقة.'],
  REC028: ['اقصر الاستنتاج على أدلة الاختبار', 'أعد صياغة الاستنتاجات لتشير فقط إلى الاختبار المرفوع وأدلة توصيف المقرر المتاحة.'],
  REC029: ['أعد حالة واحدة فقط', 'صحّح تنفيذ القاعدة بحيث تعيد كل عملية تقييم حالة واحدة مسموحًا بها.'],
  REC030: ['أضف تفسيرًا مستندًا إلى الأدلة', 'وضّح كيف تدعم الأدلة المذكورة المتطلب والحالة المحددة.'],
  REC031: ['اطلب دليلًا مفقودًا لنواتج التعلم', 'اطلب قسم نواتج تعلم مكتملًا ومقروءًا قبل إعادة فحوص نواتج التعلم.'],
  REC032: ['اطلب دليلًا مفقودًا للموضوعات', 'اطلب قسم موضوعات مقرر مكتملًا ومقروءًا قبل إعادة فحوص الموضوعات.'],
  REC033: ['اطلب دليل درجات مقروءًا', 'اطلب نسخة أوضح من الاختبار عندما يتعذر استخراج الدرجات بموثوقية.'],
  REC034: ['اطلب تعليمات مقروءة', 'اطلب نسخة أوضح من الاختبار عندما يتعذر قراءة نص التعليمات.'],
  REC035: ['اطلب دليل التقييم', 'اطلب قسم التقييم المطلوب والمكتمل في توصيف المقرر.'],
}

const BALANCED_RECOMMENDATIONS_EN: Readonly<Record<string, readonly [string, string]>> = {
  REC001: [
    'Review the question-to-CLO relationship',
    'Review the question against the cited CLO. Keep or clarify the relationship only when the confirmed evidence supports it; otherwise leave it unassigned.',
  ],
  REC005: [
    'Review intended CLO representation',
    'First confirm that this CLO was intended to be represented in this exam. If so, consider adjusting an affected question or documenting where it is assessed; a new question is not automatically required.',
  ],
  REC007: [
    'Verify the approved course specification',
    'Verify the approved course specification. If the topic is officially included but missing from the uploaded specification, update the specification. Otherwise, review or replace the question.',
  ],
  REC008: [
    'Verify the approved course specification',
    'Verify the approved course specification. If the topic is officially included but missing from the uploaded specification, update the specification. Otherwise, review or replace the question.',
  ],
  REC009: [
    'Review intended topic representation',
    'First confirm which topics were intended for this exam. If a documented topic should be represented, consider the smallest appropriate adjustment to an affected question; do not add content solely to satisfy the analyzer.',
  ],
  REC031: [
    'Request readable CLO evidence',
    'If the official populated CLO section exists but is unreadable or incomplete in the upload, provide a readable official copy. Do not create missing course information solely for this analysis.',
  ],
  REC032: [
    'Request readable topic evidence',
    'If the official populated topic section exists but is unreadable or incomplete in the upload, provide a readable official copy. Do not create missing course information solely for this analysis.',
  ],
}

const BALANCED_RECOMMENDATIONS_AR: Readonly<Record<string, readonly [string, string]>> = {
  REC001: ['راجع علاقة السؤال بناتج التعلم', 'راجع السؤال مقابل ناتج التعلم المشار إليه، وأبقِ العلاقة أو وضّحها فقط عندما تدعمها الأدلة المؤكدة، وإلا فاترك السؤال دون ربط.'],
  REC005: ['راجع تمثيل ناتج التعلم المقصود', 'تحقق أولًا من أن ناتج التعلم كان مقصودًا لهذا الاختبار. إذا كان كذلك، ففكّر في تعديل سؤال متأثر أو توثيق موضع تقييمه؛ ولا يلزم إضافة سؤال جديد تلقائيًا.'],
  REC007: ['تحقّق من توصيف المقرر المعتمد', 'تحقّق من توصيف المقرر المعتمد. إذا كان الموضوع معتمدًا لكنه غير مدرج في الملف المرفوع، فحدّث التوصيف؛ وإلا فراجع السؤال أو استبدله.'],
  REC008: ['تحقّق من توصيف المقرر المعتمد', 'تحقّق من توصيف المقرر المعتمد. إذا كان الموضوع معتمدًا لكنه غير مدرج في الملف المرفوع، فحدّث التوصيف؛ وإلا فراجع السؤال أو استبدله.'],
  REC009: ['راجع تمثيل الموضوعات المقصودة', 'تحقق أولًا من الموضوعات المقصودة لهذا الاختبار. إذا كان ينبغي تمثيل موضوع موثق، ففكّر في أصغر تعديل مناسب لسؤال متأثر، ولا تضف محتوى لمجرد إرضاء المحلل.'],
  REC031: ['اطلب دليلًا مقروءًا لنواتج التعلم', 'إذا كان القسم الرسمي المعبأ لنواتج التعلم موجودًا لكنه غير مقروء أو ناقصًا في الملف المرفوع، فقدّم نسخة رسمية مقروءة. لا تنشئ معلومات مقرر مفقودة لمجرد هذا التحليل.'],
  REC032: ['اطلب دليلًا مقروءًا للموضوعات', 'إذا كان القسم الرسمي المعبأ للموضوعات موجودًا لكنه غير مقروء أو ناقصًا في الملف المرفوع، فقدّم نسخة رسمية مقروءة. لا تنشئ معلومات مقرر مفقودة لمجرد هذا التحليل.'],
}

const STATUS_EXPLANATIONS_AR: Readonly<Record<AcademicStatus, string>> = {
  Satisfied: 'تشير الأدلة المرتبطة إلى استيفاء هذا المتطلب.',
  'Partially Satisfied': 'تشير الأدلة المرتبطة إلى استيفاء هذا المتطلب جزئيًا مع وجود جوانب تحتاج إلى مراجعة.',
  'Not Satisfied': 'تشير الأدلة المرتبطة إلى عدم استيفاء هذا المتطلب في الاختبار المرفوع.',
  'Not Verified': 'تعذر التحقق من هذا المتطلب بسبب عدم كفاية الأدلة المتاحة أو قابليتها للقراءة.',
  'Not Applicable': 'هذا المتطلب غير منطبق على الأدلة المتاحة في هذا الاختبار.',
}

function presentCourseSpecificationTerminology(original: string): string {
  return original
    .replaceAll('TP-153 Course Specification', 'Course Specification')
    .replaceAll('TP-153', 'Course Specification')
}

export function presentRequirementName(id: string, original: string, locale: Locale): string {
  return locale === 'ar'
    ? (REQUIREMENT_NAMES_AR[id] ?? 'متطلب تقييم محكوم')
    : presentCourseSpecificationTerminology(original)
}

export function presentRuleName(id: string, original: string, locale: Locale): string {
  const requirementId = id.replace(/^RULE/, 'REQ')
  return locale === 'ar'
    ? (REQUIREMENT_NAMES_AR[requirementId] ?? 'قاعدة تقييم محكومة')
    : presentCourseSpecificationTerminology(original)
}

export function presentGovernedLabel(original: string, locale: Locale): string {
  if (locale !== 'ar') return presentCourseSpecificationTerminology(original)
  return DIMENSIONS_AR[original] ?? META_AR[original] ?? 'بيان محكوم'
}

export function presentFindingExplanation(finding: FindingResponse, locale: Locale): string {
  if (locale !== 'ar') {
    return presentCourseSpecificationTerminology(finding.explanation)
  }
  const requirement = presentRequirementName(
    finding.requirement_id,
    finding.requirement_name,
    locale,
  )
  return `${STATUS_EXPLANATIONS_AR[finding.status]} ينطبق الحكم على «${requirement}» فقط ضمن نطاق الأدلة المعروضة.`
}

export function presentRecommendation(
  recommendation: RecommendationResponse,
  locale: Locale,
): { title: string; text: string; targetUser: string; type: string } {
  if (locale !== 'ar') {
    const balanced = BALANCED_RECOMMENDATIONS_EN[recommendation.recommendation_id]
    return {
      title: presentCourseSpecificationTerminology(balanced?.[0] ?? recommendation.title),
      text: presentCourseSpecificationTerminology(balanced?.[1] ?? recommendation.text),
      targetUser: recommendation.target_user,
      type: recommendation.recommendation_type,
    }
  }
  const translated = BALANCED_RECOMMENDATIONS_AR[recommendation.recommendation_id]
    ?? RECOMMENDATIONS_AR[recommendation.recommendation_id]
  return {
    title: translated?.[0] ?? 'راجع التوصية المرتبطة',
    text: translated?.[1] ?? 'راجع نتيجة التقييم والأدلة المرتبطة واتخذ الإجراء الأكاديمي المناسب.',
    targetUser: META_AR[recommendation.target_user] ?? 'المستخدم المعني',
    type: META_AR[recommendation.recommendation_type] ?? 'توصية',
  }
}
