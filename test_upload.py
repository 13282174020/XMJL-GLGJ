from web_system.template_analyzer import DocumentAnalyzer
from web_system.template_preprocessor import TemplatePreprocessor

doc_path = '03-临平区数字慈善系统建设方案模板.docx'

print('='*60)
print('分析文档')
print('='*60)

analyzer = DocumentAnalyzer()
report = analyzer.analyze(doc_path)

print(f'\n样式使用：{report.styles_usage}')
print(f'潜在标题样式：{report.potential_heading_styles}')

print('\n映射规则:')
rules = report.generate_mapping_rules()
for rule in rules:
    print(f"  {rule['source_style']} + {rule.get('pattern', 'None')} -> {rule['target_style']}")

print('\n' + '='*60)
print('预处理文档')
print('='*60)

preprocessor = TemplatePreprocessor()
result = preprocessor.preprocess(doc_path, 'tests/fixtures/test_processed.docx', rules)

print(f'\n结果：{result.message}')
print(f'统计：{result.stats}')
