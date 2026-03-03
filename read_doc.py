# -*- coding: utf-8 -*-
import zipfile
import re
import os

# 获取当前目录
cwd = os.getcwd()
print(f"当前目录：{cwd}")

# 查找文件
for f in os.listdir(cwd):
    if f.endswith('.docx') and '软件建设方案' in f:
        filepath = os.path.join(cwd, f)
        print(f"找到文件：{f}, 大小：{os.path.getsize(filepath)}")
        
        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                print(f"文件内容：{z.namelist()[:10]}")
                if 'word/document.xml' in z.namelist():
                    xml = z.read('word/document.xml').decode('utf-8')
                    print(f"文档 XML 长度：{len(xml)}")
                    # 提取文本
                    texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)
                    print("\n=== 提取的文本内容 ===")
                    full_text = '\n'.join(texts)
                    print(full_text)
        except Exception as e:
            print(f"读取错误：{e}")
        break
