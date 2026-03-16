from web_system.template_analyzer import DocumentAnalyzer 
from web_system.template_preprocessor import TemplatePreprocessor 
  
analyzer = DocumentAnalyzer()  
report = analyzer.analyze('tests/fixtures/sample_nonstandard.docx')  
  
print('=== Analysis Report ===')  
print(f'Potential heading styles: {report.potential_heading_styles}')  
print(f'Styles usage: {report.styles_usage}') 
  
print('\n=== Heading Styles Details ===')  
for name, analysis in report.heading_styles.items():  
    print(f'{name}:')  
    print(f'  is_heading={analysis.is_heading}, level={analysis.heading_level}')  
    print(f'  numbering_patterns count: {len(analysis.numbering_patterns)}')  
    if analysis.numbering_patterns:  
        for p, info in analysis.numbering_patterns.items():  
            print(f'    {p} -> Level {info.suggested_level}, Count: {info.count}') 
  
print('\n=== Mapping Rules ===')
rules = report.generate_mapping_rules()
print(f'Rules count: {len(rules)}')
for rule in rules:
    print(f"  Source: {rule['source_style']}, Pattern: {rule.get('pattern')}, Target: {rule['target_style']}")
  
print('\n=== Test Preprocess ===')  
preprocessor = TemplatePreprocessor()  
result = preprocessor.preprocess('tests/fixtures/sample_nonstandard.docx', 'tests/fixtures/test_output.docx', rules)  
print(f'Result: {result.message}')  
print(f'Stats: {result.stats}') 
