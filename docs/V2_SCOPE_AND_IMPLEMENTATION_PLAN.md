# AI Exam Quality Platform — Version 2 Plan

**Release:** `v2.0.0-arabic-pilot`  
**Timebox:** أقل من أسبوع  
**Primary user:** Faculty Member  
**Release type:** Controlled multi-user pilot

## الهدف
تحويل Version 1 إلى منصة يستطيع أي عضو هيئة تدريس التسجيل فيها، امتلاك Dashboard وسجل تحليلات خاص، رفع اختبار وCourse Specification، مراجعة الاستخراج، تشغيل التحليل، مشاهدة النتائج، وتنزيل تقرير عربي أو إنجليزي.

## السكوب الأساسي المعتمد

### 1) الحسابات وتعدد المستخدمين
- Sign up, sign in, sign out, password reset.
- دور واحد فقط: Faculty Member.
- كل مستخدم يرى ملفاته وتحليلاته وتقاريره فقط.
- حماية روابط الملفات والتقارير وواجهات API.
- دعم أكثر من مستخدم وتحليل في الوقت نفسه.

### 2) Dashboard خاص بالدكتور
- عرض التحليلات السابقة وحالتها.
- فتح النتائج وتحميل التقرير.
- إظهار حالة: قيد المعالجة، يحتاج مراجعة، مكتمل، فشل.

### 3) المصطلحات في الواجهة
يستخدم النظام:
- **Exam / الاختبار**
- **Course Specification / توصيف المقرر**

لا يظهر TP-153 كاسم رئيسي. يمكن ذكره فقط كمثال على أحد النماذج المدعومة.

### 4) دعم العربية والإنجليزية
- اختبار عربي أو إنجليزي أو مختلط.
- Course Specification عربي أو إنجليزي أو مختلط.
- أرقام عربية وإنجليزية.
- ترقيم مثل: س١، س1، السؤال الأول، Question 1.
- أسئلة فرعية: أ، ب، ج و a, b, c.
- نص عربي يحتوي مصطلحات أو كود إنجليزي.

### 5) OCR عربي وإنجليزي
المسار:
`direct text extraction -> quality check -> OCR when needed -> normalization -> review`

يجب حفظ الصفحة والموقع والثقة، وعدم تجاوز مراجعة المستخدم عند انخفاض الثقة.

### 6) Adaptive Course Specification Parser
يدعم اكتشاف بنية نماذج مختلفة تلقائيًا باستخدام العناوين والجداول والدلالات والموقع، ثم يحولها إلى Schema موحدة تشمل:
- بيانات المقرر.
- CLOs.
- Topics.
- Assessment Methods عند توفرها.
- Contact Hours عند توفرها.

لا يخترع النظام أي CLO أو Topic أو نسبة مفقودة. عند انخفاض الثقة يعرض البيانات للمراجعة بدل التخمين.

### 7) إكمال القواعد الست
- RULE014: Referenced Material Availability.
- RULE015: Supporting Material Legibility.
- RULE016: Supporting Material Association.
- RULE017: Visible Marks.
- RULE020: Exam Identification.
- RULE022: Resolvable Cross-References.

كل قاعدة تحتاج Evidence، Page provenance، Applicability gate، الحالات الأكاديمية المعتمدة، واختبارات للحالات الصحيحة والخاطئة والغامضة والمفقودة.

### 8) تصنيف أنواع الأسئلة
الأنواع:
- Multiple Choice
- True / False
- Matching
- Fill in the Blank
- Short Answer
- Essay
- Calculation / Problem Solving
- Programming / Coding
- Code Tracing / Debugging
- Practical
- Multi-part / Mixed
- Unclassified

لكل سؤال: النوع، High/Medium/Low confidence، وإمكانية التصحيح أثناء Extraction Review.

### 9) توزيع أنواع الأسئلة والدرجات
- عدد الأسئلة من كل نوع.
- النسبة من إجمالي الأسئلة.
- مجموع الدرجات لكل نوع.
- النسبة من إجمالي الدرجات.
- تنبيه وصفي عند التركّز الكبير في نوع واحد.

التنبيه لا يؤثر على Overall Score دون سياسة معتمدة.

### 10) Methodology Page
تشرح بلغة بسيطة:
- ماذا تحلل المنصة؟
- كيف يتم الاستخراج وOCR؟
- لماذا توجد مراجعة بشرية؟
- ماذا تعني الحالات؟
- ماذا يعني Not Verified؟
- كيف يتم تصنيف أنواع الأسئلة؟
- حدود المنصة وما لا تقوم به؟

### 11) إشعارات داخل المنصة
- Analysis completed.
- Review required.
- Processing failed.
- Report ready.

البريد الإلكتروني مؤجل.

### 12) تقارير PDF ثنائية اللغة
- Arabic RTL وEnglish LTR.
- نتائج القواعد الست.
- توزيع أنواع الأسئلة والدرجات.
- الأدلة والصفحات.
- Missing Evidence والتوصيات.
- لغة الملف وطريقة الاستخراج.

## المؤجل
- مقارنة نسختين من الاختبار.
- سجل تغييرات مرئي ومفصل.
- أدوار Admin وQuality Reviewer.
- محرك سياسات مؤسسية كامل.
- الاشتراكات والمدفوعات.
- تحليل إجابات الطلاب والصعوبة الحقيقية.
- LMS/API integrations.

## خطة التنفيذ خلال 6 أيام

### اليوم 1 — Audit + Authentication + Ownership
- تشغيل اختبارات Version 1 كـ baseline.
- فحص الهوية الحالية.
- إنشاء الحسابات والجلسات.
- إضافة user ownership لكل التحليلات والملفات والتقارير.
- حماية المسارات وإضافة اختبارات العزل.

**Exit gate:** مستخدمان لا يستطيع أي منهما فتح بيانات الآخر.

### اليوم 2 — Arabic Extraction + OCR
- اكتشاف اللغة.
- Arabic normalization.
- OCR عربي وإنجليزي.
- حفظ page geometry والثقة.
- Fixtures عربية رقمية وممسوحة ومختلطة.

**Exit gate:** الأسئلة والدرجات والترقيم والصفحات محفوظة بصورة صحيحة في ملفات القبول.

### اليوم 3 — Adaptive Course Specification Parser
- اكتشاف الأقسام والعناوين والجداول.
- استخراج CLOs وTopics إلى Schema موحدة.
- دعم TP-153 وتخطيطين مختلفين على الأقل.
- Low-confidence review behavior.

**Exit gate:** ثلاثة نماذج مختلفة تصل إلى review-ready دون اختراع بيانات.

### اليوم 4 — RULE014 + RULE016 + RULE022
- استخراج وربط figures, tables, code blocks, labels.
- حل المراجع الداخلية والغموض.
- Evidence drill-down والاختبارات.

### اليوم 5 — RULE015 + RULE017 + RULE020 + Question Types
- مؤشرات مقاسة لوضوح المواد.
- ظهور الدرجات وتعريف الاختبار.
- تصنيف الأنواع وإمكانية التصحيح.
- توزيع الأنواع والدرجات.

### اليوم 6 — UI + Methodology + Notifications + Reports + Full Tests
- واجهة عربية/إنجليزية وRTL/LTR للرحلة الأساسية.
- تغيير TP-153 إلى Course Specification في الواجهة.
- Methodology والإشعارات.
- PDF عربي/إنجليزي.
- اختبارات Backend, Frontend, Integration, Docker.

## Release blockers
لا يتم إصدار النسخة إذا:
- مستخدم يستطيع الوصول لبيانات مستخدم آخر.
- Development identity ما زالت مفعلة.
- الملفات أو التقارير عامة.
- العربية أو الترقيم أو الدرجات تتلف في ملفات القبول.
- OCR يتجاوز المراجعة البشرية.
- Course Specification parser يخترع بيانات.
- قاعدة جديدة تعطي حكمًا دون Evidence كافٍ.
- توزيع أنواع الأسئلة يؤثر على الدرجة دون سياسة.
- التقرير العربي غير مقروء.
- اختبارات Version 1 الأساسية تتراجع.

## قاعدة التحكم بالسكوب
- لا إضافات جديدة أثناء هذا الأسبوع.
- لا تغيير لمعنى Knowledge Base.
- لا Thresholds أو سياسات مخترعة.
- اختبار لكل Feature.
- Plan قبل أي تعديل برمجي.
