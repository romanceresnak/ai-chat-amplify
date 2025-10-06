import json
import boto3
import os
import logging
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import zipfile
import io
import xml.etree.ElementTree as ET
import re
import base64
from abc import ABC, abstractmethod

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')
TEMPLATE_PROCESSOR_ARN = os.environ.get('TEMPLATE_PROCESSOR_ARN', f'arn:aws:lambda:eu-west-1:873478944520:function:scribbe-ai-{ENVIRONMENT}-template-processor')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

def create_basic_powerpoint(instructions: str, timestamp: str) -> bytes:
    """Create a basic PowerPoint file using OpenXML format without external dependencies"""
    
    # Create a ZIP file in memory (PowerPoint is essentially a ZIP archive)
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as pptx_zip:
        
        # Add [Content_Types].xml
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
</Types>'''
        pptx_zip.writestr('[Content_Types].xml', content_types)
        
        # Add _rels/.rels
        main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''
        pptx_zip.writestr('_rels/.rels', main_rels)
        
        # Add ppt/_rels/presentation.xml.rels
        pres_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>'''
        pptx_zip.writestr('ppt/_rels/presentation.xml.rels', pres_rels)
        
        # Add ppt/presentation.xml
        truncated_instructions = instructions[:200] + "..." if len(instructions) > 200 else instructions
        presentation_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''
        pptx_zip.writestr('ppt/presentation.xml', presentation_xml)
        
        # Add ppt/slides/slide1.xml
        slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="Title 1"/>
                    <p:cNvSpPr>
                        <a:spLocks noGrp="1"/>
                    </p:cNvSpPr>
                    <p:nvPr>
                        <p:ph type="ctrTitle"/>
                    </p:nvPr>
                </p:nvSpPr>
                <p:spPr/>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US" sz="4400"/>
                            <a:t>Financial Analysis Presentation</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="3" name="Subtitle 2"/>
                    <p:cNvSpPr>
                        <a:spLocks noGrp="1"/>
                    </p:cNvSpPr>
                    <p:nvPr>
                        <p:ph type="subTitle" idx="1"/>
                    </p:nvPr>
                </p:nvSpPr>
                <p:spPr/>
                <p:txBody>
                    <a:bodyPr/>
                    <a:lstStyle/>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US" sz="2400"/>
                            <a:t>Generated on {timestamp}</a:t>
                        </a:r>
                    </a:p>
                    <a:p>
                        <a:r>
                            <a:rPr lang="en-US" sz="2000"/>
                            <a:t>{truncated_instructions}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''
        pptx_zip.writestr('ppt/slides/slide1.xml', slide_xml)
        
        # Add minimal theme, slideMaster, and slideLayout files
        theme_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
    <a:themeElements>
        <a:clrScheme name="Office">
            <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
            <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
            <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
            <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
            <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
            <a:accent2><a:srgbClr val="F79646"/></a:accent2>
            <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
            <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
            <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
            <a:accent6><a:srgbClr val="F366A7"/></a:accent6>
            <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
            <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
        </a:clrScheme>
        <a:fontScheme name="Office">
            <a:majorFont>
                <a:latin typeface="Calibri Light"/>
            </a:majorFont>
            <a:minorFont>
                <a:latin typeface="Calibri"/>
            </a:minorFont>
        </a:fontScheme>
        <a:fmtScheme name="Office">
            <a:fillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
            </a:fillStyleLst>
            <a:lnStyleLst>
                <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
            </a:lnStyleLst>
            <a:effectStyleLst>
                <a:effectStyle><a:effectLst/></a:effectStyle>
            </a:effectStyleLst>
            <a:bgFillStyleLst>
                <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
            </a:bgFillStyleLst>
        </a:fmtScheme>
    </a:themeElements>
</a:theme>'''
        pptx_zip.writestr('ppt/theme/theme1.xml', theme_xml)
        
        # Add minimal slide master
        slide_master_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
    <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
    </p:sldLayoutIdLst>
</p:sldMaster>'''
        pptx_zip.writestr('ppt/slideMasters/slideMaster1.xml', slide_master_xml)
        
        # Add minimal slide layout
        slide_layout_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="titleOnly" preserve="1">
    <p:cSld name="Title Only">
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sldLayout>'''
        pptx_zip.writestr('ppt/slideLayouts/slideLayout1.xml', slide_layout_xml)
        
        # Add relationship files for slide master
        slide_master_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''
        pptx_zip.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', slide_master_rels)
        
        slide_layout_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''
        pptx_zip.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', slide_layout_rels)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def modify_existing_powerpoint(pptx_content: bytes, modifications: Dict[str, Any]) -> bytes:
    """Modify an existing PowerPoint file while preserving ALL content"""
    
    # Create a new ZIP buffer for the modified PPTX
    modified_zip_buffer = io.BytesIO()
    
    logger.info(f"Starting modification with: {modifications}")
    
    # Read the existing PPTX
    with zipfile.ZipFile(io.BytesIO(pptx_content), 'r') as source_zip:
        with zipfile.ZipFile(modified_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as modified_zip:
            
            slide_count = 0
            target_slide_number = modifications.get('slide_number')
            
            # Copy ALL files from source to modified zip
            for file_info in source_zip.infolist():
                file_content = source_zip.read(file_info.filename)
                
                # Check if this is a slide file
                if file_info.filename.startswith('ppt/slides/slide') and file_info.filename.endswith('.xml'):
                    slide_count += 1
                    
                    # Only modify the target slide if specified
                    if target_slide_number is None or slide_count == target_slide_number:
                        logger.info(f"Modifying slide {slide_count}: {file_info.filename}")
                        file_content = modify_slide_content(file_content, modifications)
                    else:
                        logger.info(f"Preserving slide {slide_count}: {file_info.filename}")
                
                # Check if this is a chart file that needs modification
                elif file_info.filename.startswith('ppt/charts/chart') and file_info.filename.endswith('.xml'):
                    # Only modify charts if this is the target slide
                    if target_slide_number is None or True:  # For now, modify all charts
                        logger.info(f"Modifying chart: {file_info.filename}")
                        file_content = modify_chart_content(file_content, modifications)
                    else:
                        logger.info(f"Preserving chart: {file_info.filename}")
                
                # Copy the file (modified or original) to the new PPTX
                modified_zip.writestr(file_info.filename, file_content)
            
            logger.info(f"Processed {slide_count} slides total")
    
    modified_zip_buffer.seek(0)
    return modified_zip_buffer.getvalue()

def modify_slide_content(slide_xml_content: bytes, modifications: Dict[str, Any]) -> bytes:
    """Modify text content in a slide"""
    try:
        # Parse the XML
        root = ET.fromstring(slide_xml_content)
        
        # Define namespaces
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
        }
        
        # Check if this slide should be modified based on slide number
        slide_number = modifications.get('slide_number')
        if slide_number:
            # Extract slide number from filename to check if this is the target slide
            # This is a simplistic approach - in reality you'd need more sophisticated targeting
            logger.info(f"Targeting slide number: {slide_number}")
        
        # Find all text elements and apply modifications
        for text_mod in modifications.get('text_replacements', []):
            find_text = text_mod.get('find', '')
            replace_text = text_mod.get('replace', '')
            
            # Find all text elements
            for text_elem in root.findall('.//a:t', namespaces):
                if text_elem.text and find_text in text_elem.text:
                    text_elem.text = text_elem.text.replace(find_text, replace_text)
                    logger.info(f"Replaced '{find_text}' with '{replace_text}'")
        
        # If we have a title modification, try to set it as the main title
        title = modifications.get('title')
        if title:
            # Find title placeholder and update it
            for text_elem in root.findall('.//a:t', namespaces):
                # Look for typical title patterns or placeholders
                if text_elem.text and ('title' in text_elem.text.lower() or len(text_elem.text) < 50):
                    text_elem.text = title
                    logger.info(f"Set slide title to: {title}")
                    break
        
        # Convert back to string
        return ET.tostring(root, encoding='utf-8')
        
    except Exception as e:
        logger.error(f"Error modifying slide content: {str(e)}")
        return slide_xml_content

def modify_chart_content(chart_xml_content: bytes, modifications: Dict[str, Any]) -> bytes:
    """Modify chart data in a chart XML file"""
    try:
        # Parse the XML
        root = ET.fromstring(chart_xml_content)
        
        # Define namespaces for chart XML
        namespaces = {
            'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        
        # Apply chart data modifications
        for chart_mod in modifications.get('chart_data', []):
            chart_type = chart_mod.get('type', '')
            new_data = chart_mod.get('data', [])
            
            if chart_type == 'bar_chart':
                modify_bar_chart_data(root, new_data, namespaces)
            elif chart_type == 'line_chart':
                modify_line_chart_data(root, new_data, namespaces)
        
        # Convert back to string
        return ET.tostring(root, encoding='utf-8')
        
    except Exception as e:
        logger.error(f"Error modifying chart content: {str(e)}")
        return chart_xml_content

def modify_bar_chart_data(root: ET.Element, new_data: list, namespaces: dict):
    """Modify bar chart data values"""
    try:
        # Find bar chart series
        for ser in root.findall('.//c:barChart/c:ser', namespaces):
            # Find values element
            val_elem = ser.find('c:val', namespaces)
            if val_elem is not None:
                # Find numeric reference
                num_ref = val_elem.find('c:numRef', namespaces)
                if num_ref is not None:
                    # Update the data
                    num_cache = num_ref.find('c:numCache', namespaces)
                    if num_cache is not None:
                        # Update point count
                        pt_count = num_cache.find('c:ptCount', namespaces)
                        if pt_count is not None:
                            pt_count.set('val', str(len(new_data)))
                        
                        # Clear existing points
                        for pt in num_cache.findall('c:pt', namespaces):
                            num_cache.remove(pt)
                        
                        # Add new data points
                        for i, value in enumerate(new_data):
                            pt = ET.SubElement(num_cache, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                            pt.set('idx', str(i))
                            v = ET.SubElement(pt, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                            v.text = str(value)
                            
    except Exception as e:
        logger.error(f"Error modifying bar chart data: {str(e)}")

def modify_line_chart_data(root: ET.Element, new_data: list, namespaces: dict):
    """Modify line chart data values"""
    try:
        # Find line chart series
        for ser in root.findall('.//c:lineChart/c:ser', namespaces):
            # Find values element
            val_elem = ser.find('c:val', namespaces)
            if val_elem is not None:
                # Find numeric reference
                num_ref = val_elem.find('c:numRef', namespaces)
                if num_ref is not None:
                    # Update the data
                    num_cache = num_ref.find('c:numCache', namespaces)
                    if num_cache is not None:
                        # Update point count
                        pt_count = num_cache.find('c:ptCount', namespaces)
                        if pt_count is not None:
                            pt_count.set('val', str(len(new_data)))
                        
                        # Clear existing points
                        for pt in num_cache.findall('c:pt', namespaces):
                            num_cache.remove(pt)
                        
                        # Add new data points
                        for i, value in enumerate(new_data):
                            pt = ET.SubElement(num_cache, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                            pt.set('idx', str(i))
                            v = ET.SubElement(pt, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                            v.text = str(value)
                            
    except Exception as e:
        logger.error(f"Error modifying line chart data: {str(e)}")

def parse_pptx_structure(pptx_content: bytes) -> Dict[str, Any]:
    """Parse PPTX structure to understand slides, charts, and text elements"""
    structure = {
        'slides': [],
        'charts': [],
        'text_elements': []
    }
    
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_content), 'r') as zip_file:
            # Find all slide files
            for filename in zip_file.namelist():
                if filename.startswith('ppt/slides/slide') and filename.endswith('.xml'):
                    slide_content = zip_file.read(filename)
                    slide_info = analyze_slide_content(slide_content, filename)
                    structure['slides'].append(slide_info)
                
                elif filename.startswith('ppt/charts/chart') and filename.endswith('.xml'):
                    chart_content = zip_file.read(filename)
                    chart_info = analyze_chart_content(chart_content, filename)
                    structure['charts'].append(chart_info)
    
    except Exception as e:
        logger.error(f"Error parsing PPTX structure: {str(e)}")
    
    return structure

def analyze_slide_content(slide_xml_content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze slide content to extract text elements"""
    slide_info = {
        'filename': filename,
        'text_elements': [],
        'shapes': []
    }
    
    try:
        root = ET.fromstring(slide_xml_content)
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
        }
        
        # Find all text elements
        for text_elem in root.findall('.//a:t', namespaces):
            if text_elem.text:
                slide_info['text_elements'].append(text_elem.text)
        
        # Find shapes
        for shape in root.findall('.//p:sp', namespaces):
            shape_info = {'type': 'shape'}
            # Get shape name if available
            name_elem = shape.find('.//p:cNvPr', namespaces)
            if name_elem is not None:
                shape_info['name'] = name_elem.get('name', '')
            slide_info['shapes'].append(shape_info)
    
    except Exception as e:
        logger.error(f"Error analyzing slide content: {str(e)}")
    
    return slide_info

def analyze_chart_content(chart_xml_content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze chart content to extract data series"""
    chart_info = {
        'filename': filename,
        'chart_type': '',
        'series': []
    }
    
    try:
        root = ET.fromstring(chart_xml_content)
        namespaces = {
            'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        
        # Detect chart type
        if root.find('.//c:barChart', namespaces) is not None:
            chart_info['chart_type'] = 'bar'
        elif root.find('.//c:lineChart', namespaces) is not None:
            chart_info['chart_type'] = 'line'
        elif root.find('.//c:pieChart', namespaces) is not None:
            chart_info['chart_type'] = 'pie'
        
        # Extract series data
        for ser in root.findall('.//c:ser', namespaces):
            series_info = {'values': []}
            
            # Get series values
            val_elem = ser.find('c:val', namespaces)
            if val_elem is not None:
                num_ref = val_elem.find('c:numRef', namespaces)
                if num_ref is not None:
                    num_cache = num_ref.find('c:numCache', namespaces)
                    if num_cache is not None:
                        for pt in num_cache.findall('c:pt', namespaces):
                            v_elem = pt.find('c:v', namespaces)
                            if v_elem is not None and v_elem.text:
                                series_info['values'].append(float(v_elem.text))
            
            chart_info['series'].append(series_info)
    
    except Exception as e:
        logger.error(f"Error analyzing chart content: {str(e)}")
    
    return chart_info

def parse_instructions_to_modifications(instructions: str) -> Dict[str, Any]:
    """Parse user instructions to extract slide number, text changes, and chart data"""
    modifications = {
        'slide_number': None,
        'text_replacements': [],
        'chart_data': [],
        'title': None
    }
    
    try:
        # Extract slide number
        slide_match = re.search(r'slide\s+(\d+)', instructions.lower())
        if slide_match:
            modifications['slide_number'] = int(slide_match.group(1))
        
        # Extract title
        title_match = re.search(r'titled\s+"([^"]+)"', instructions, re.IGNORECASE)
        if title_match:
            modifications['title'] = title_match.group(1)
            modifications['text_replacements'].append({
                'find': 'Financial Analysis Presentation',  # Default title in basic template
                'replace': title_match.group(1)
            })
        
        # Extract chart data - look for dollar amounts and percentages
        dollar_amounts = re.findall(r'\$(\d+(?:,\d+)*(?:\.\d+)?)M', instructions)
        percentages = re.findall(r'(\d+\.\d+)%', instructions)
        
        if dollar_amounts:
            # Convert to numbers (remove commas)
            chart_values = [float(amount.replace(',', '')) for amount in dollar_amounts]
            modifications['chart_data'].append({
                'type': 'bar_chart',
                'data': chart_values
            })
        
        if percentages:
            # Convert percentages to numbers
            percentage_values = [float(pct) for pct in percentages]
            modifications['chart_data'].append({
                'type': 'line_chart', 
                'data': percentage_values
            })
        
        # Extract highlights/bullet points
        highlights_match = re.search(r'highlights.*?listing:\s*(.+?)(?:,\s*styled|$)', instructions, re.IGNORECASE | re.DOTALL)
        if highlights_match:
            highlights_text = highlights_match.group(1)
            # Replace any existing highlights section
            modifications['text_replacements'].append({
                'find': 'Generated on',  # This will be in the subtitle area
                'replace': f"2Q'20 Highlights:\n{highlights_text}"
            })
    
    except Exception as e:
        logger.error(f"Error parsing instructions: {str(e)}")
    
    return modifications

def cors_response(status_code: int, body: dict) -> Dict[str, Any]:
    """Helper function to always return CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(body)
    }

def list_presentations() -> Dict[str, Any]:
    """List all presentations from S3"""
    try:
        logger.info("Listing presentations from S3")
        
        response = s3.list_objects_v2(
            Bucket=OUTPUT_BUCKET,
            Delimiter='/'
        )
        
        presentations = []
        
        # Get all folders (each folder represents a presentation)
        for prefix in response.get('CommonPrefixes', []):
            presentation_id = prefix['Prefix'].rstrip('/')
            
            # List files in this presentation folder
            files_response = s3.list_objects_v2(
                Bucket=OUTPUT_BUCKET,
                Prefix=prefix['Prefix']
            )
            
            if 'Contents' in files_response:
                for obj in files_response['Contents']:
                    file_key = obj['Key']
                    file_name = file_key.split('/')[-1]
                    
                    # Generate presigned URL for download
                    download_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': OUTPUT_BUCKET, 'Key': file_key},
                        ExpiresIn=3600  # 1 hour
                    )
                    
                    presentations.append({
                        'id': presentation_id,
                        'name': file_name,
                        'key': file_key,
                        'created': obj['LastModified'].isoformat(),
                        'size': obj['Size'],
                        'download_url': download_url
                    })
        
        logger.info(f"Found {len(presentations)} presentations")
        
        return cors_response(200, {
            'presentations': presentations,
            'count': len(presentations)
        })
        
    except Exception as e:
        logger.error(f"Error listing presentations: {str(e)}", exc_info=True)
        return cors_response(500, {
            'error': 'Failed to list presentations',
            'message': str(e)
        })

# Agent Base Class
class Agent(ABC):
    """Base class for all agents"""
    
    @abstractmethod
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request and return response"""
        pass

# Presentation Agent
class PresentationAgent(Agent):
    """Agent for handling PowerPoint generation and modification"""
    
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process presentation generation request"""
        try:
            instructions = request.get('instructions', '')
            template_key = request.get('template_key', 'PUBLIC IP South Plains (1).pptx')
            mode = request.get('mode', 'modify')
            
            # Generate unique presentation ID
            presentation_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            logger.info(f"PresentationAgent processing: {presentation_id}")
            
            if mode == 'modify' and template_key:
                # Modify existing presentation
                return self._modify_presentation(presentation_id, instructions, template_key)
            else:
                # Create new presentation
                return self._create_presentation(presentation_id, instructions, timestamp)
                
        except Exception as e:
            logger.error(f"PresentationAgent error: {str(e)}")
            return {
                'error': 'Failed to process presentation',
                'message': str(e),
                'agent': 'presentation'
            }
    
    def _modify_presentation(self, presentation_id: str, instructions: str, template_key: str) -> Dict[str, Any]:
        """Modify existing presentation"""
        # Download existing PPTX from S3
        template_response = s3.get_object(Bucket='scribbe-ai-dev-documents', Key=template_key)
        existing_pptx_content = template_response['Body'].read()
        
        logger.info(f"Downloaded existing PPTX from S3: {template_key}")
        
        # Parse instructions to modifications
        modifications = parse_instructions_to_modifications(instructions)
        
        # Apply modifications
        modified_pptx_content = modify_existing_powerpoint(existing_pptx_content, modifications)
        
        # Save modified PowerPoint file to S3
        output_key = f"{presentation_id}/PUBLIC_IP_South_Plains_modified.pptx"
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=modified_pptx_content,
            ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        
        logger.info(f"Modified PowerPoint saved to S3: {output_key}")
        
        # Generate presigned URL for download
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUTPUT_BUCKET, 'Key': output_key},
            ExpiresIn=3600
        )
        
        return {
            'presentation_id': presentation_id,
            'output_url': f"s3://{OUTPUT_BUCKET}/{output_key}",
            'message': 'Presentation modified successfully!',
            'presentation_name': output_key.split('/')[-1],
            'download_url': download_url,
            'status': 'success',
            'mode': 'modify',
            'agent': 'presentation'
        }
    
    def _create_presentation(self, presentation_id: str, instructions: str, timestamp: str) -> Dict[str, Any]:
        """Create new presentation"""
        pptx_content = create_basic_powerpoint(instructions, timestamp)
        
        # Save PowerPoint file to S3
        output_key = f"{presentation_id}/presentation.pptx"
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=pptx_content,
            ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        
        logger.info(f"New PowerPoint saved to S3: {output_key}")
        
        # Generate presigned URL for download
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUTPUT_BUCKET, 'Key': output_key},
            ExpiresIn=3600
        )
        
        return {
            'presentation_id': presentation_id,
            'output_url': f"s3://{OUTPUT_BUCKET}/{output_key}",
            'message': 'Presentation created successfully!',
            'presentation_name': output_key.split('/')[-1],
            'download_url': download_url,
            'status': 'success',
            'mode': 'create',
            'agent': 'presentation'
        }

# Chat Agent
class ChatAgent(Agent):
    """Agent for handling Q&A and general chat using Bedrock"""
    
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process chat request using Bedrock Claude"""
        try:
            message = request.get('instructions', '')
            files = request.get('files', [])
            
            logger.info(f"ChatAgent processing message: {message[:100]}...")
            
            # Prepare the prompt
            prompt = self._prepare_prompt(message, files)
            
            # Call Bedrock Claude
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps({
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "anthropic_version": "bedrock-2023-05-31"
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            assistant_message = response_body['content'][0]['text']
            
            return {
                'message': assistant_message,
                'status': 'success',
                'agent': 'chat'
            }
            
        except Exception as e:
            logger.error(f"ChatAgent error: {str(e)}")
            return {
                'error': 'Failed to process chat',
                'message': 'Sorry, I encountered an error while processing your request.',
                'agent': 'chat'
            }
    
    def _prepare_prompt(self, message: str, files: List[str]) -> str:
        """Prepare prompt with context from files if provided"""
        prompt = message
        
        if files:
            prompt += "\n\nContext from uploaded files:\n"
            for file_key in files[:3]:  # Limit to first 3 files
                try:
                    # Download file content from S3
                    file_obj = s3.get_object(Bucket='scribbe-ai-dev-storage', Key=file_key)
                    content = file_obj['Body'].read().decode('utf-8', errors='ignore')
                    prompt += f"\n--- File: {file_key} ---\n{content[:1000]}...\n"
                except Exception as e:
                    logger.error(f"Error reading file {file_key}: {str(e)}")
        
        return prompt

# Document Agent
class DocumentAgent(Agent):
    """Agent for analyzing and extracting information from documents"""
    
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process document analysis request"""
        try:
            message = request.get('instructions', '')
            files = request.get('files', [])
            
            if not files:
                return {
                    'message': 'Please upload a document to analyze.',
                    'status': 'error',
                    'agent': 'document'
                }
            
            logger.info(f"DocumentAgent analyzing {len(files)} files")
            
            # Analyze documents using Bedrock
            analysis_prompt = f"""Analyze the following documents and {message}.
            
            Documents:"""
            
            for file_key in files:
                try:
                    # Download file content
                    file_obj = s3.get_object(Bucket='scribbe-ai-dev-storage', Key=file_key)
                    content = file_obj['Body'].read().decode('utf-8', errors='ignore')
                    analysis_prompt += f"\n\n--- {file_key} ---\n{content[:2000]}"
                except Exception as e:
                    logger.error(f"Error reading file {file_key}: {str(e)}")
            
            # Call Bedrock for analysis
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps({
                    "messages": [{
                        "role": "user",
                        "content": analysis_prompt
                    }],
                    "max_tokens": 1500,
                    "temperature": 0.3,
                    "anthropic_version": "bedrock-2023-05-31"
                })
            )
            
            response_body = json.loads(response['body'].read())
            analysis_result = response_body['content'][0]['text']
            
            return {
                'message': analysis_result,
                'status': 'success',
                'agent': 'document',
                'files_analyzed': len(files)
            }
            
        except Exception as e:
            logger.error(f"DocumentAgent error: {str(e)}")
            return {
                'error': 'Failed to analyze documents',
                'message': str(e),
                'agent': 'document'
            }

# Main Orchestrator Agent
class OrchestratorAgent:
    """Main orchestrator that routes requests to appropriate agents"""
    
    def __init__(self):
        self.agents = {
            'presentation': PresentationAgent(),
            'chat': ChatAgent(),
            'document': DocumentAgent()
        }
    
    def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate agent based on intent"""
        try:
            instructions = request.get('instructions', '')
            files = request.get('files', [])
            
            logger.info(f"OrchestratorAgent routing request: {instructions[:100]}...")
            
            # Determine which agent to use
            agent_type = self._determine_agent(instructions, files)
            logger.info(f"Selected agent: {agent_type}")
            
            # Process request with selected agent
            agent = self.agents[agent_type]
            response = agent.process(request)
            
            # Add routing metadata
            response['routed_to'] = agent_type
            response['timestamp'] = datetime.utcnow().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"OrchestratorAgent error: {str(e)}")
            return {
                'error': 'Routing error',
                'message': str(e),
                'status': 'error'
            }
    
    def _determine_agent(self, instructions: str, files: List[str]) -> str:
        """Determine which agent should handle the request"""
        lower_instructions = instructions.lower()
        
        # Check for presentation-related keywords
        presentation_keywords = ['slide', 'powerpoint', 'ppt', 'presentation', 'deck']
        if any(keyword in lower_instructions for keyword in presentation_keywords):
            return 'presentation'
        
        # Check if this is a document analysis request
        document_keywords = ['analyze', 'extract', 'summarize', 'review']
        if files and any(keyword in lower_instructions for keyword in document_keywords):
            return 'document'
        
        # Default to chat agent
        return 'chat'

# Global orchestrator instance
orchestrator = OrchestratorAgent()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Multi-Agent orchestrator Lambda handler.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check HTTP method
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'GET':
            # List presentations
            return list_presentations()
        
        # Parse request for POST
        body_str = event.get('body', '{}')
        if not body_str:
            body_str = '{}'
        body = json.loads(body_str)
        
        # Extract request parameters
        request = {
            'instructions': body.get('instructions', ''),
            'template_key': body.get('template_key', 'PUBLIC IP South Plains (1).pptx'),
            'document_key': body.get('document_key', ''),
            'files': body.get('files', []),
            'mode': body.get('mode', 'modify'),
            'analyze_structure': body.get('analyze_structure', False)
        }
        
        # Route request through orchestrator
        response = orchestrator.route_request(request)
        
        # Return CORS-safe response
        return cors_response(200, response)
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        return cors_response(500, {
            'error': 'Internal server error',
            'message': str(e),
            'status': 'error'
        })