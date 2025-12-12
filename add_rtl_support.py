import os
import re

def apply_rtl_changes():
    # مسیر پوشه تمپلیت‌ها
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    
    print(f"Scanning directory: {templates_dir} ...")
    
    # 1. Regex for HTML tag 
    # این الگو تگ html را پیدا می‌کند (چه lang="en" باشد چه داینامیک) و ویژگی‌های دیگر را حفظ می‌کند
    html_tag_regex = re.compile(r'<html\s+lang=[\'"](?:en|\{\{\s*get_locale\(\)\s*\}\})[\'"]\s*([^>]*)>')
    
    # 2. Regex for Bootstrap CSS
    # این الگو لینک استاندارد بوت‌استرپ 5.3.3 را پیدا می‌کند
    bootstrap_regex = re.compile(r'(<link\s+href=[\'"]https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.3/dist/css/bootstrap\.min\.css[\'"][^>]*>)')
    
    modified_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # --- Step 1: Update HTML Tag ---
                # فقط اگر قبلاً شرط RTL اضافه نشده باشد
                if 'dir="rtl"' not in content:
                    def html_replacement(match):
                        attrs = match.group(1)
                        # تگ جدید با زبان داینامیک و شرط راست‌چین
                        return f'<html lang="{{{{ get_locale() }}}}" {attrs} {{% if get_locale() == \'fa\' %}}dir="rtl"{{% endif %}}>'
                    
                    content = html_tag_regex.sub(html_replacement, content)

                # --- Step 2: Update Bootstrap CSS ---
                # sadece اگر نسخه RTL قبلاً اضافه نشده باشد
                if 'bootstrap.rtl.min.css' not in content:
                    rtl_block = (
                        "{% if get_locale() == 'fa' %}\n"
                        "    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css\" rel=\"stylesheet\">\n"
                        "    {% else %}\n"
                        "    \\1\n"
                        "    {% endif %}"
                    )
                    content = bootstrap_regex.sub(rtl_block, content)
                
                # ذخیره تغییرات در صورت وجود تفاوت
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Updated: {file}")
                    modified_count += 1
                    
    print(f"\nDone! Modified {modified_count} files.")

if __name__ == "__main__":
    apply_rtl_changes()