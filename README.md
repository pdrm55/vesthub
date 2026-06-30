# VestHub

پلتفرم سرمایه‌گذاری مبتنی بر Flask با مدیریت پلن‌ها، توزیع سود روزانه، سیستم معرف (referral)،
احراز هویت دو‌مرحله‌ای (2FA)، KYC، پشتیبانی تیکتی و پنل مدیریت کامل.

> ⚠️ این پروژه **لایو** است و با پول واقعی کاربران کار می‌کند. پیش از هر تغییر، بخش‌های
> «Cron Jobs» و «Backup & Restore» و فایل [`SECURITY_TODO.md`](SECURITY_TODO.md) را بخوانید.

---

## فهرست
- [امکانات](#امکانات)
- [پشته‌ی فناوری](#پشتهی-فناوری)
- [ساختار پروژه](#ساختار-پروژه)
- [راه‌اندازی](#راهاندازی)
- [متغیرهای محیطی (.env)](#متغیرهای-محیطی-env)
- [مقداردهی اولیه‌ی دیتابیس](#مقداردهی-اولیهی-دیتابیس)
- [اجرا (development و production)](#اجرا)
- [⏰ Cron Jobs (الزامی)](#-cron-jobs-الزامی)
- [دستورهای CLI](#دستورهای-cli)
- [منطق توزیع سود](#منطق-توزیع-سود)
- [Backup & Restore](#backup--restore)
- [امنیت](#امنیت)

---

## امکانات
- ثبت‌نام/ورود با ایمیل + ورود با Google (OAuth)
- تأیید ایمیل، احراز هویت دو‌مرحله‌ای (TOTP / Google Authenticator)
- پلن‌های سرمایه‌گذاری با نرخ سود سالانه و مدت دوره
- **توزیع سود روزانه** با سیستم backfill/جبران روزهای ازقلم‌افتاده
- پاداش معرف (referral bonus)
- درخواست برداشت با تأیید دومرحله‌ای (کد ایمیل + TOTP)
- KYC و آپلود مدارک با اعتبارسنجی نوع فایل
- پشتیبانی تیکتی، پنل ادمین (کاربران، پلن‌ها، پرداخت‌ها، برداشت‌ها، حسابداری، لاگ‌ها)
- چندزبانه (انگلیسی/ترکی/فارسی) با Flask-Babel

## پشته‌ی فناوری
- **Backend:** Python, Flask 3, SQLAlchemy 2, Flask-Login, Flask-WTF (CSRF), Flask-Mail, Flask-Babel, Authlib
- **Auth/2FA:** PyOTP, itsdangerous (توکن بازنشانی رمز)
- **Server:** Gunicorn (پشت Nginx/Cloudflare) با Unix socket + `ProxyFix`
- **DB:** پیش‌فرض SQLite (پیشنهاد مهاجرت به PostgreSQL — رجوع به `SECURITY_TODO.md`)
- **Scheduling:** cron سیستم‌عامل (نه APScheduler)

## ساختار پروژه
```
vesthub/
├── app.py              # کارخانه‌ی اپ، Babel/locale، error handlers، CLI commands
├── config.py           # کلاس‌های Config (Development/Production)
├── extensions.py       # نمونه‌های unbound افزونه‌ها
├── models.py           # مدل‌های دیتابیس (User, Investment, Transaction, ...)
├── decorators.py       # permission_required / admin_required
├── utils.py            # دسترسی‌ها، موجودی قابل‌برداشت، آپلود فایل، ارسال ایمیل
├── tasks.py            # توزیع/بازیابی سود روزانه (process_missed_profits)
├── seed.py             # ساخت نقش‌ها و ادمین اولیه
├── routes/
│   ├── auth.py         # ثبت‌نام، ورود، 2FA، بازنشانی رمز، OAuth
│   ├── main.py         # صفحات عمومی، API بازار
│   ├── user.py         # داشبورد، سرمایه‌گذاری، برداشت، KYC، تیکت
│   └── admin.py        # پنل مدیریت
├── templates/ , static/ , translations/
├── run_daily_profit.sh # اسکریپت cron توزیع سود
└── requirements.txt
```

## راه‌اندازی
```bash
git clone https://github.com/pdrm55/vesthub.git
cd vesthub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # سپس مقادیر را پر کنید (نمونه‌ی کلیدها در بخش بعد)
```

## متغیرهای محیطی (.env)
فایل `.env` در ریشه‌ی پروژه (در `.gitignore` است و نباید commit شود):

| کلید | توضیح |
|------|-------|
| `SECRET_KEY` | **الزامی.** کلید امضای سشن و توکن‌ها. حداقل ۶۴ کاراکتر hex (`python -c "import secrets;print(secrets.token_hex(32))"`). بدون آن، با هر ری‌استارت سشن‌ها باطل می‌شوند. |
| `APP_ENV` | `production` (پیش‌فرض) یا `development`. روی production کوکی‌های امن و `DEBUG=False` فعال می‌شود. |
| `DATABASE_URL` | رشته‌ی اتصال دیتابیس. پیش‌فرض SQLite در `instance/vesthub.db`. |
| `MAIL_SERVER` / `MAIL_PORT` | سرور SMTP و پورت (پیش‌فرض ۵۸۷). |
| `MAIL_USE_TLS` / `MAIL_USE_SSL` | `True`/`False`. |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | اعتبارنامه‌ی SMTP. |
| `MAIL_DEFAULT_SENDER_NAME` / `MAIL_DEFAULT_SENDER_EMAIL` | نام و ایمیل فرستنده. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | برای ساخت ادمین اولیه در `seed.py` (در غیر این صورت ادمین ساخته نمی‌شود). |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | برای ورود با Google. |

> نکته: `FLASK_APP=app.py` نیز برای دستورهای `flask` لازم است (در `.env` یا محیط).

## مقداردهی اولیه‌ی دیتابیس
```bash
source venv/bin/activate
python seed.py        # ساخت جداول + نقش‌های Admin/Investor/Support + ادمین اولیه
```

## اجرا

### Development (محلی)
```bash
APP_ENV=development FLASK_APP=app.py flask run        # یا: python app.py
```

### Production (Gunicorn + systemd)
سرویس از طریق `systemd` اجرا می‌شود (`/etc/systemd/system/vesthub.service`):
```ini
ExecStart=/home/ubuntu/vesthub/venv/bin/gunicorn --workers 3 --bind unix:vesthub.sock -m 007 app:app
```
دستورهای مدیریت سرویس:
```bash
sudo systemctl restart vesthub      # بعد از هر تغییر کد
sudo systemctl status vesthub
sudo journalctl -u vesthub -f       # مشاهده‌ی لاگ زنده
```
Nginx به socket `vesthub.sock` پروکسی می‌کند؛ اپ پشت `ProxyFix` و معمولاً Cloudflare قرار دارد
(هدر `CF-IPCountry` برای تشخیص زبان استفاده می‌شود).

---

## ⏰ Cron Jobs (الزامی)
این cronها **بخشی از دیتابیس یا کد نیستند** و باید روی **هر سرور** جداگانه با `crontab -e`
(کاربر `ubuntu`) تنظیم شوند. بدون مورد اول، **سود کاربران توزیع نمی‌شود**.

```cron
# توزیع/بازیابی سود — هر ساعت سرِ دقیقه‌ی صفر (الزامی)
0 * * * * /home/ubuntu/vesthub/run_daily_profit.sh

# یادآور بازاریابی — هر روز ساعت ۱۰ صبح (اختیاری)
0 10 * * * cd /home/ubuntu/vesthub && /home/ubuntu/vesthub/venv/bin/flask send-marketing-reminders >> /home/ubuntu/vesthub/logs/marketing_cron.log 2>&1
```

- **`run_daily_profit.sh`** → داخلش `flask recover-profits` را اجرا می‌کند که `process_missed_profits`
  را صدا می‌زند: برای هر سرمایه‌گذاری `active`، سود همه‌ی روزهای پرداخت‌نشده تا امروز (و تا سررسید)
  را با محافظت در برابر تکراری‌بودن می‌سازد. اجرای ساعتی صرفاً برای اطمینان از جبران است؛ هر روز فقط
  یک‌بار سود ثبت می‌شود.
- مطمئن شوید `run_daily_profit.sh` قابل‌اجراست: `chmod +x run_daily_profit.sh`.
- لاگ‌ها در `logs/cron_profit.log` و `logs/marketing_cron.log`.

## دستورهای CLI
```bash
flask recover-profits          # توزیع/جبران دستی سود (همان چیزی که cron اجرا می‌کند)
flask send-marketing-reminders # ارسال ایمیل بازاریابی به کاربران بدون سرمایه‌گذاری بعد از ۳ روز
flask test-email <email>       # ارسال ایمیل تست به یک آدرس
```

## منطق توزیع سود
- سود روزانه: `amount × (annual_return_rate / 100) / 365`.
- شروع از `last_profit_date + ۱ روز` (یا `start_date` اگر هنوز سودی نخورده) تا
  **کمینه‌ی «امروز» و «تاریخ سررسید»**.
- **تاریخ سررسید (`end_date`)** هنگام تأیید پرداخت توسط ادمین، برابر `start_date + duration_months`
  تنظیم می‌شود؛ برای رکوردهای قدیمی بدون `end_date`، در اولین اجرای task محاسبه و ذخیره می‌گردد.
  پس از سررسید، **دیگر سودی تعلق نمی‌گیرد**.
- پاداش معرف: درصدی از سود روزانه (از تنظیم `referral_percentage`، پیش‌فرض ۲٪) به معرفِ کاربر.
- اجرای task **idempotent** است (چک `existing_tx` برای هر روز).

## Backup & Restore
هنگام بازگرداندن یک بکاپ قدیمی روی سرور جدید:
1. دیتابیس را برگردانید و `.env` را با مقادیر درست تنظیم کنید (به‌ویژه `SECRET_KEY`).
2. **cronها را روی سرور جدید دوباره تنظیم کنید** (بکاپ دیتابیس شامل crontab نیست).
3. یک‌بار دستی اجرا کنید تا روزهای جاافتاده پر شوند:
   ```bash
   cd /home/ubuntu/vesthub && FLASK_APP=app.py venv/bin/flask recover-profits
   ```
   سیستم backfill، سودِ همه‌ی روزهای بین تاریخ بکاپ تا امروز را برای سرمایه‌گذاری‌های `active`
   به‌صورت خودکار می‌سازد (تا سررسید).

> 🔴 توجه: backfill **فقط** تراکنش‌های `profit` و `referral_bonus` را بازسازی می‌کند. هر داده‌ی
> دیگری که بعد از بکاپ روی سرور قبلی ایجاد شده باشد (ثبت‌نام، واریز، برداشت، KYC، تیکت) و در بکاپ
> نباشد، **بازنمی‌گردد**. اگر سایت قبلی در فاصله‌ی بکاپ تا مهاجرت فعال بوده، آن داده‌ها از دست می‌روند.

## امنیت
- CSRF به‌صورت سراسری فعال است (Flask-WTF).
- رمزها با `pbkdf2:sha256` هش می‌شوند.
- برداشت نیازمند KYC تأییدشده + 2FA فعال + تأیید کد ایمیل و TOTP است.
- فعال‌سازی سرمایه‌گذاری **فقط** از طریق تأیید ادمین (`admin.approve_payment`) ممکن است.
- کارهای امنیتی/زیرساختی باقی‌مانده در [`SECURITY_TODO.md`](SECURITY_TODO.md) فهرست شده‌اند
  (مهاجرت به PostgreSQL، Flask-Limiter، Flask-Talisman و ...).

---
© VestHub
