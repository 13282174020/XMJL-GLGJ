# -*- coding: utf-8 -*-
import pytest
from web_system.app import get_heading_level, scan_template_styles

def test_heading_1():
    assert get_heading_level('Heading 1') == 1

def test_heading_6():
    assert get_heading_level('Heading 6') == 6

def test_not_heading():
    assert get_heading_level('Normal') == 0

def test_scan_standard(sample_standard_doc):
    result = scan_template_styles(str(sample_standard_doc))
    assert result['success'] is True
    print('OK:', result['message'])

def test_scan_nonstandard(sample_nonstandard_doc):
    result = scan_template_styles(str(sample_nonstandard_doc))
    assert result['success'] is True
    print('OK:', result['message'])
