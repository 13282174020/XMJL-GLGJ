# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'e:\Qwen\xmjl')
content = '''# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'e:\Qwen\xmjl')
from web_system.ai_engine import clean_ai_content
print('Test')
result = clean_ai_content('½¨Òé½áºÏ²âÊÔ', '½¨Òé')
print('Result:', result)
'''
with open('e:\Qwen\xmjl\test_clean_ai.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
