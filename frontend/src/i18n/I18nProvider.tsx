/* eslint-disable react-refresh/only-export-components -- provider, catalog, and companion hook share this module. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Locale } from '../types/api'
import { ADDITIONAL_ARABIC_MESSAGES } from './additionalArabicMessages'

const STORAGE_KEY = 'exam-quality-analyzer-locale'

const BASE_ARABIC_MESSAGES: Record<string, string> = {
  'Faculty access': 'دخول أعضاء هيئة التدريس',
  'Open your private dashboard and continue your exam-quality analyses.': 'افتح لوحة التحكم الخاصة بك وتابع تحليلات جودة الاختبارات.',
  'Email address': 'البريد الإلكتروني',
  'New to the platform?': 'مستخدم جديد؟',
  'Create a faculty account': 'إنشاء حساب لعضو هيئة تدريس',
  'Faculty registration': 'تسجيل عضو هيئة تدريس',
  'Create your account': 'إنشاء حسابك',
  'Already have an account?': 'لديك حساب بالفعل؟',
  'Full name': 'الاسم الكامل',
  'Institution': 'الجهة التعليمية',
  'Create account': 'إنشاء الحساب',
  'Creating account…': 'جارٍ إنشاء الحساب…',
  'Could not create account': 'تعذر إنشاء الحساب',
  'Account recovery': 'استعادة الحساب',
  'Enter your account email. The response does not reveal whether an account exists.': 'أدخل البريد الإلكتروني المرتبط بالحساب. لن تكشف الاستجابة ما إذا كان الحساب موجودًا.',
  'Send reset instructions': 'إرسال تعليمات إعادة التعيين',
  'Requesting…': 'جارٍ الإرسال…',
  'Request received': 'تم استلام الطلب',
  'Return to sign in': 'العودة إلى تسجيل الدخول',
  'Could not request reset': 'تعذر إرسال طلب إعادة التعيين',
  'Reset your password': 'إعادة تعيين كلمة المرور',
  'Choose a new password': 'اختر كلمة مرور جديدة',
  'New password': 'كلمة المرور الجديدة',
  'Confirm new password': 'تأكيد كلمة المرور الجديدة',
  'Update password': 'تحديث كلمة المرور',
  'Updating password…': 'جارٍ تحديث كلمة المرور…',
  'Password updated': 'تم تحديث كلمة المرور',
  'Sign in using your new password.': 'سجّل الدخول باستخدام كلمة المرور الجديدة.',
  'Exam Quality Analyzer': 'محلل جودة الاختبارات',
  'Analysis-assisted': 'مدعوم بالتحليل',
  'This evaluation is advisory and intended to support faculty review. Final academic responsibility remains with the instructor.': 'هذا التقييم استرشادي ويهدف إلى دعم مراجعة عضو هيئة التدريس، وتبقى المسؤولية الأكاديمية النهائية على المدرّس.',
  'Derived advisory relationship': 'علاقة استرشادية مستنتجة',
  'Academic quality support': 'دعم الجودة الأكاديمية',
  Dashboard: 'لوحة التحكم',
  Analyses: 'التحليلات',
  'All analyses': 'جميع التحليلات',
  'New Analysis': 'تحليل جديد',
  'New analysis': 'تحليل جديد',
  'Analysis': 'التحليل',
  'Analysis Progress': 'تقدم التحليل',
  'Start Analysis': 'بدء التحليل',
  'Starting…': 'جارٍ البدء…',
  'Retry Analysis': 'إعادة محاولة التحليل',
  'Retrying…': 'جارٍ إعادة المحاولة…',
  'Analysis processing failed': 'فشلت معالجة التحليل',
  'Analysis processing progress': 'تقدم معالجة التحليل',
  'Connection interrupted': 'انقطع الاتصال',
  'Extraction ready for review': 'الاستخراج جاهز للمراجعة',
  'Continue to Review and Start': 'المتابعة إلى المراجعة والبدء',
  'Confirm Extraction and Continue': 'تأكيد الاستخراج والمتابعة',
  'All changes saved': 'تم حفظ جميع التغييرات',
  'Report': 'التقرير',
  'Report language': 'لغة التقرير',
  'Generate Report': 'إنشاء التقرير',
  'Generating…': 'جارٍ الإنشاء…',
  'Download PDF': 'تحميل PDF',
  'Downloading…': 'جارٍ التحميل…',
  'Report generated': 'تم إنشاء التقرير',
  'No reports have been generated yet.': 'لم يتم إنشاء أي تقارير بعد.',
  'Loading report history…': 'جارٍ تحميل سجل التقارير…',
  'Retry report history': 'إعادة محاولة تحميل سجل التقارير',
  'KB version': 'إصدار قاعدة المعرفة',
  'Insufficient Evidence': 'أدلة غير كافية',
  'Satisfied': 'مستوفى',
  'Partially Satisfied': 'مستوفى جزئيًا',
  'Not Satisfied': 'غير مستوفى',
  'Not Verified': 'غير متحقق',
  'Not Applicable': 'غير منطبق',
  'High': 'مرتفع',
  'Medium': 'متوسط',
  'Low': 'منخفض',
  'Questions': 'الأسئلة',
  'Question': 'السؤال',
  'Child question': 'سؤال فرعي',
  'Parent question': 'سؤال رئيسي',
  'Marks': 'الدرجات',
  'Page': 'الصفحة',
  'Status': 'الحالة',
  'Action': 'الإجراء',
  'Course code': 'رمز المقرر',
  'Course name': 'اسم المقرر',
  'Department': 'القسم',
  'Program': 'البرنامج',
  'Term': 'الفصل الدراسي',
  'Midterm': 'اختبار نصفي',
  'Final': 'اختبار نهائي',
  'Upload Documents': 'رفع المستندات',
  'Both documents are required': 'المستندان مطلوبان',
  'Choose file': 'اختيار ملف',
  'Remove file': 'إزالة الملف',
  'Sign in': 'تسجيل الدخول',
  'Sign out': 'تسجيل الخروج',
  'Email': 'البريد الإلكتروني',
  'Password': 'كلمة المرور',
  'Confirm password': 'تأكيد كلمة المرور',
  'Display name': 'الاسم المعروض',
  'Forgot password?': 'هل نسيت كلمة المرور؟',
  'Reset password': 'إعادة تعيين كلمة المرور',
  'Save': 'حفظ',
  'Cancel': 'إلغاء',
  'Close': 'إغلاق',
  'Back': 'رجوع',
  'Continue': 'متابعة',
  'Loading…': 'جارٍ التحميل…',
  'Try again': 'إعادة المحاولة',
  'Skip to main content': 'الانتقال إلى المحتوى الرئيسي',
  'Application navigation': 'التنقل في التطبيق',
  'Open navigation': 'فتح قائمة التنقل',
  'Close navigation': 'إغلاق قائمة التنقل',
  'Overview': 'نظرة عامة',
  'Alignment & Coverage': 'المواءمة والتغطية',
  'Findings & Recommendations': 'النتائج والتوصيات',
  'Marks & Structure': 'الدرجات والبنية',
  'Recommendations': 'التوصيات',
  'Evidence': 'الأدلة',
  'Score': 'النتيجة',
  'Completed': 'مكتمل',
  'Failed': 'فشل',
  'Queued': 'في الانتظار',
  'Current backend stage': 'مرحلة المعالجة الحالية',
  'validating': 'التحقق من الملفات',
  'extracting_exam': 'استخراج الاختبار',
  'extracting_tp153': 'استخراج توصيف المقرر',
  'review_ready': 'جاهز لمراجعة الاستخراج',
  'building_evidence': 'بناء الأدلة',
  'retrieving_knowledge': 'استرجاع المعرفة',
  'applying_rules': 'تطبيق القواعد',
  'generating_report': 'إكمال التحليل',
  'completed': 'مكتمل',
  'failed': 'فشل',
}

export const ARABIC_MESSAGES: Readonly<Record<string, string>> = {
  ...BASE_ARABIC_MESSAGES,
  ...ADDITIONAL_ARABIC_MESSAGES,
}

const MISSING_ARABIC_MESSAGE = 'تعذر عرض النص المترجم.'

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string, variables?: Record<string, string | number>) => string
  formatDateTime: (value: string | Date) => string
}

const defaultI18nContext: I18nContextValue = {
  locale: 'en',
  setLocale: () => undefined,
  t: (key, variables) => {
    let translated = key
    for (const [name, value] of Object.entries(variables ?? {})) {
      translated = translated.replaceAll(`{${name}}`, String(value))
    }
    return translated
  },
  formatDateTime: (value) =>
    new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(value instanceof Date ? value : new Date(value)),
}

const I18nContext = createContext<I18nContextValue>(defaultI18nContext)

function initialLocale(): Locale {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'ar' || stored === 'en') return stored
  return 'ar'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale)

  const setLocale = useCallback((nextLocale: Locale): void => {
    setLocaleState(nextLocale)
    window.localStorage.setItem(STORAGE_KEY, nextLocale)
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'
    document.title = locale === 'ar' ? 'محلل جودة الاختبارات' : 'Exam Quality Analyzer'
  }, [locale])

  const t = useCallback(
    (key: string, variables?: Record<string, string | number>): string => {
      let translated =
        locale === 'ar' ? (ARABIC_MESSAGES[key] ?? MISSING_ARABIC_MESSAGE) : key
      for (const [name, value] of Object.entries(variables ?? {})) {
        translated = translated.replaceAll(`{${name}}`, String(value))
      }
      return translated
    },
    [locale],
  )

  const formatDateTime = useCallback(
    (value: string | Date): string =>
      new Intl.DateTimeFormat(locale === 'ar' ? 'ar-SA' : 'en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(value instanceof Date ? value : new Date(value)),
    [locale],
  )

  const contextValue = useMemo(
    () => ({ locale, setLocale, t, formatDateTime }),
    [locale, setLocale, t, formatDateTime],
  )

  return <I18nContext.Provider value={contextValue}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext)
}
