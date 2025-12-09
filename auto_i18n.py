import os
import re

# مسیر پوشه تمپلیت‌ها
TEMPLATES_DIR = 'templates'

# تگ‌هایی که محتوایشان نباید ترجمه شود
IGNORE_TAGS = ['script', 'style', 'code', 'pre', 'textarea']

# ویژگی‌هایی (Attributes) که باید ترجمه شوند
TRANSLATABLE_ATTRS = ['placeholder', 'title', 'alt', 'aria-label']

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. ترجمه متن‌های بین تگ‌ها (Text Nodes)
    # تغییر: حذف \n از لیست سیاه برای پشتیبانی از متن‌های چندخطی
    def wrap_text(match):
        prefix = match.group(1) # >
        raw_text = match.group(2) # محتوای متنی
        suffix = match.group(3) # <
        
        # اگر متن فقط فاصله خالی است یا قبلاً ترجمه شده، دست نزن
        if not raw_text.strip() or '{{' in raw_text or '{%' in raw_text or '_(' in raw_text:
            return match.group(0)
        
        # اگر متن خیلی کوتاه یا فقط عدد است، نادیده بگیر
        clean_text = raw_text.strip()
        if len(clean_text) < 2 or clean_text.isdigit():
            return match.group(0)

        # مدیریت کوتیشن‌ها برای جلوگیری از ارور Syntax
        # اگر در متن تک‌کوتیشن (') وجود دارد، از دابل‌کوتیشن (") استفاده کن
        quote_char = "'"
        if "'" in clean_text:
            quote_char = '"'
            # اگر دابل‌کوتیشن هم در متن بود، باید اسکیپ شود (که البته در HTML نادر است)
            if '"' in clean_text:
                clean_text = clean_text.replace('"', '\\"')

        # حفظ ساختار فاصله‌ها در HTML (مهم برای چندخطی‌ها)
        # ما کل متن را با نسخه تمیز شده جایگزین می‌کنیم
        # اما برای HTML بهتر است فاصله‌های اینتر را نرمال کنیم
        normalized_text = ' '.join(clean_text.split())
        
        # ساخت رشته نهایی
        return f"{prefix}{{{{ _({quote_char}{normalized_text}{quote_char}) }}}}{suffix}"

    # پترن جدید: اجازه می‌دهد متن شامل خط جدید باشد، اما تگ‌های باز/بسته (< >) و کدهای جینجا ({ }) را نادیده می‌گیرد
    # نکته: این Regex باز هم کامل نیست اما برای اکثر فایل‌های HTML استاندارد کار می‌کند
    pattern_text = r'(>)([^<>{}]+?)(<)'
    content = re.sub(pattern_text, wrap_text, content, flags=re.DOTALL)

    # 2. ترجمه ویژگی‌ها (Attributes) مثل placeholder
    for attr in TRANSLATABLE_ATTRS:
        def wrap_attr(match):
            start = match.group(1) # placeholder="
            text = match.group(2)  # متن داخل
            end = match.group(3)   # "
            
            if not text.strip() or '{{' in text:
                return match.group(0)
            
            # تعیین نوع کوتیشن
            quote_char = "'"
            if "'" in text:
                quote_char = '"'

            return f"{start}{{{{ _({quote_char}{text}{quote_char}) }}}}{end}"

        pattern_attr = f'({attr}=["\'])([^"\']{{2,}})(["\'])'
        content = re.sub(pattern_attr, wrap_attr, content)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {file_path}")
        return True
    return False

def main():
    if not os.path.exists(TEMPLATES_DIR):
        print("Folder not found!")
        return

    print("🤖 Starting Smart Auto-Translation Wrapper...")
    count = 0
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        for file in files:
            if file.endswith('.html'):
                if process_file(os.path.join(root, file)):
                    count += 1
    
    print(f"\n🎉 Done! Modified {count} files.")

if __name__ == '__main__':
    main()