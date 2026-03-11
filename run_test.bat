@echo off  
echo Testing get_heading_level...  
python -c \"import sys; sys.path.insert(0, 'web_system'); from app import get_heading_level; print('L1:', get_heading_level('Heading 1', '╣зр╩уб')); print('L5:', get_heading_level('Heading 5', '1.1.1.1.1')); print('L6:', get_heading_level('Heading 6', '1.1.1.1.1.1'))\"  
pause 
