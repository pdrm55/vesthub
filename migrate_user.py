import sqlite3
import os
import shutil

def add_marketing_column():
    # لیست مسیرهای احتمالی دیتابیس
    possible_paths = [
        'vesthub.db',
        'instance/vesthub.db',
        '/home/ubuntu/vesthub/instance/vesthub.db', # مسیر احتمالی در VPS
        '/home/ubuntu/vesthub/vesthub.db'
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            # چک کردن اینکه آیا واقعا دیتابیس است و جدول users دارد
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cursor.fetchone():
                    db_path = path
                    conn.close()
                    break
                conn.close()
            except:
                continue

    if not db_path:
        print("❌ Error: Could not find 'vesthub.db' with a 'users' table.")
        print("Please check if your database is in the 'instance' folder or has a different name.")
        return

    print(f"Found database at: {db_path}")
    
    # ۱. پشتیبان‌گیری
    backup_path = db_path + '.backup'
    shutil.copyfile(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # ۲. اضافه کردن ستون جدید
        cursor.execute("ALTER TABLE users ADD COLUMN marketing_email_sent BOOLEAN DEFAULT 0")
        
        conn.commit()
        print("🚀 Success: 'marketing_email_sent' column added safely to 'users' table.")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Notice: Column already exists. No changes needed.")
        else:
            print(f"❌ SQL Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_marketing_column()