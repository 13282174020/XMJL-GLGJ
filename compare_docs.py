# -*- coding: utf-8 -*-
import zipfile
import re

def extract_docx_text(filepath):
    """提取 docx 文档文本和样式信息"""
    with zipfile.ZipFile(filepath, 'r') as z:
        if 'word/document.xml' not in z.namelist():
            print(f"无法找到 document.xml in {filepath}")
            return []
        
        xml = z.read('word/document.xml').decode('utf-8')
        
        # 提取段落文本和样式
        paragraphs = []
        para_pattern = r'<w:p[^>]*>(.*?)</w:p>'
        
        for para_match in re.finditer(para_pattern, xml, re.DOTALL):
            para_xml = para_match.group(1)
            
            # 提取样式
            style_match = re.search(r'<w:pStyle[^>]*w:val="([^"]+)"', para_xml)
            style = style_match.group(1) if style_match else 'Normal'
            
            # 提取文本
            texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', para_xml)
            text = ''.join(texts).strip()
            
            if text:
                paragraphs.append({
                    'text': text,
                    'style': style
                })
        
        return paragraphs

def analyze_structure(paragraphs, doc_name):
    """分析文档结构"""
    print(f"\n{'='*70}")
    print(f"文档：{doc_name}")
    print(f"{'='*70}")
    print(f"总段落数：{len(paragraphs)}")
    
    # 提取章节标题
    chapters = []
    for i, para in enumerate(paragraphs):
        text = para['text']
        style = para['style']
        
        # 检测章标题（第一章、第 1 章）
        if re.match(r'^第 [一二三四五六七八九十\d]+章', text):
            chapters.append({'level': 1, 'title': text, 'style': style})
        # 检测节标题（1.1, 1.1.1 等）
        elif re.match(r'^\d+\.\d+', text):
            dots = text.count('.')
            level = min(dots + 1, 4)
            chapters.append({'level': level, 'title': text[:60], 'style': style})
    
    print(f"章节标题数：{len(chapters)}")
    
    # 按章分组
    current_chapter = None
    chapter_sections = {}
    
    for ch in chapters:
        if ch['level'] == 1:
            current_chapter = ch['title']
            chapter_sections[current_chapter] = []
        elif current_chapter:
            chapter_sections[current_chapter].append(ch)
    
    # 显示第一章详细结构
    print(f"\n第一章详细结构:")
    first_chapter = None
    for title in chapter_sections.keys():
        if '第 1 章' in title or '第一章' in title or '项目概况' in title:
            first_chapter = title
            break
    
    if first_chapter:
        sections = chapter_sections[first_chapter]
        print(f"  第一章名称：{first_chapter}")
        print(f"  小节数量：{len(sections)}")
        for sec in sections:
            indent = "    " * (sec['level'] - 1)
            print(f"  {indent}L{sec['level']}: {sec['title']} [样式：{sec['style']}]")
    
    # 显示所有样式
    styles = set(p['style'] for p in paragraphs)
    print(f"\n使用的样式:")
    for s in sorted(styles)[:15]:
        print(f"  - {s}")
    
    return chapter_sections

# 提取并分析
print("正在分析模板文档...")
template_paras = extract_docx_text(r'e:\Qwen\xmjl\可行性研究报告模板.docx')
template_chapters = analyze_structure(template_paras, '可行性研究报告模板.docx')

print("\n\n正在分析 AI 生成文档...")
ai_paras = extract_docx_text(r'e:\Qwen\xmjl\AI 生成可行性研究报告.docx')
ai_chapters = analyze_structure(ai_paras, 'AI 生成可行性研究报告.docx')

# 对比
print(f"\n{'='*70}")
print("对比总结")
print(f"{'='*70}")

# 获取第一章
template_ch1 = None
ai_ch1 = None

for title in template_chapters.keys():
    if '第 1 章' in title or '第一章' in title or '项目概况' in title:
        template_ch1 = template_chapters[title]
        break

for title in ai_chapters.keys():
    if '第 1 章' in title or '第一章' in title or '项目概况' in title:
        ai_ch1 = ai_chapters[title]
        break

if template_ch1:
    print(f"\n模板第一章：{[t for t in template_chapters.keys() if '第 1 章' in t or '第一章' in t or '项目概况' in t][0]}")
    print(f"  小节总数：{len(template_ch1)}")
    l2_count = len([s for s in template_ch1 if s['level'] == 2])
    l3_count = len([s for s in template_ch1 if s['level'] == 3])
    print(f"  二级标题数：{l2_count}")
    print(f"  三级标题数：{l3_count}")

if ai_ch1:
    print(f"\nAI 生成第一章：{[t for t in ai_chapters.keys() if '第 1 章' in t or '第一章' in t or '项目概况' in t][0]}")
    print(f"  小节总数：{len(ai_ch1)}")
    l2_count = len([s for s in ai_ch1 if s['level'] == 2])
    l3_count = len([s for s in ai_ch1 if s['level'] == 3])
    print(f"  二级标题数：{l2_count}")
    print(f"  三级标题数：{l3_count}")

print("\n\n差异分析:")
if template_ch1 and ai_ch1:
    template_titles = set(s['title'] for s in template_ch1)
    ai_titles = set(s['title'] for s in ai_ch1)
    
    missing = template_titles - ai_titles
    extra = ai_titles - template_titles
    
    if missing:
        print(f"\nAI 生成文档缺失的小节:")
        for m in list(missing)[:10]:
            print(f"  - {m}")
    
    if extra:
        print(f"\nAI 生成文档多出的小节:")
        for e in list(extra)[:10]:
            print(f"  + {e}")
