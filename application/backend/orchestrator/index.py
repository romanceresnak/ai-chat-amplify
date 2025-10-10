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

# Import AI presentation generator
try:
    from ai_presentation_generator import AIPresentationGenerator
except ImportError:
    AIPresentationGenerator = None

# Load environment variables from .env file
try:
    import env_loader
    env_loader.load_env_file()
except ImportError:
    # Fallback if env_loader not available
    pass

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
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
TEMPLATE_PROCESSOR_ARN = os.environ.get('TEMPLATE_PROCESSOR_ARN', f'arn:aws:lambda:eu-west-1:873478944520:function:scribbe-ai-{ENVIRONMENT}-template-processor')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')
AUDIT_LOGGER_ARN = os.environ.get('AUDIT_LOGGER_ARN', f'arn:aws:lambda:eu-west-1:873478944520:function:scribbe-ai-{ENVIRONMENT}-audit-logger')
PATTERN_ANALYZER_ARN = os.environ.get('PATTERN_ANALYZER_ARN', f'arn:aws:lambda:eu-west-1:873478944520:function:scribbe-ai-{ENVIRONMENT}-pattern-analyzer')

# Initialize DynamoDB for pattern insights
dynamodb = boto3.resource('dynamodb')
try:
    patterns_table = dynamodb.Table(f'scribbe-ai-{ENVIRONMENT}-patterns')
except:
    patterns_table = None

def verify_user_permissions(event: Dict[str, Any], required_permission: str = 'ReadOnly') -> tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Verify user has required permissions based on Cognito groups.
    Returns: (is_authorized, user_id, user_groups)
    """
    try:
        # Extract user info from Lambda authorizer
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        
        # Get user ID and groups
        user_id = claims.get('sub') or claims.get('username', 'anonymous')
        groups_claim = claims.get('cognito:groups', [])
        
        # Ensure groups is a list
        if isinstance(groups_claim, str):
            groups = [groups_claim]
        elif isinstance(groups_claim, list):
            groups = groups_claim
        else:
            groups = []
        
        # Define permission hierarchy
        permission_levels = {
            'Admin': 3,
            'WriteAccess': 2,
            'ReadOnly': 1
        }
        
        # Get user's highest permission level
        user_level = 0
        for group in groups:
            if group in permission_levels:
                user_level = max(user_level, permission_levels[group])
        
        # Check if user has required permission
        required_level = permission_levels.get(required_permission, 1)
        is_authorized = user_level >= required_level
        
        logger.info(f"Permission check - User: {user_id}, Groups: {groups}, Required: {required_permission}, Authorized: {is_authorized}")
        
        return is_authorized, user_id, groups
        
    except Exception as e:
        logger.error(f"Error verifying permissions: {str(e)}")
        return False, None, []

def log_audit_event(user_id: str, action: str, resource: str, event_type: str, details: Dict[str, Any] = None):
    """Send audit log event to audit logger Lambda"""
    try:
        audit_payload = {
            'userId': user_id,
            'action': action,
            'resource': resource,
            'eventType': event_type,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Invoke audit logger Lambda asynchronously
        lambda_client.invoke(
            FunctionName=AUDIT_LOGGER_ARN,
            InvocationType='Event',  # Asynchronous
            Payload=json.dumps(audit_payload)
        )
        
        logger.info(f"Audit event logged: {action} by {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log audit event: {str(e)}")

def trigger_pattern_analysis(trigger_type: str, context: Dict[str, Any] = None):
    """Trigger pattern analysis Lambda for insights"""
    try:
        pattern_payload = {
            'trigger': trigger_type,
            'context': context or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Invoke pattern analyzer Lambda asynchronously
        lambda_client.invoke(
            FunctionName=PATTERN_ANALYZER_ARN,
            InvocationType='Event',  # Asynchronous
            Payload=json.dumps(pattern_payload)
        )
        
        logger.info(f"Pattern analysis triggered: {trigger_type}")
        
    except Exception as e:
        logger.error(f"Failed to trigger pattern analysis: {str(e)}")

def get_pattern_insights() -> Dict[str, Any]:
    """Get pattern insights from DynamoDB patterns table"""
    try:
        if not patterns_table:
            return {
                'error': 'Pattern insights not available',
                'total_patterns': 0,
                'insights': []
            }
        
        # Scan recent patterns (last 30 days)
        from datetime import timedelta
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        response = patterns_table.scan(
            FilterExpression='discovered_at > :cutoff',
            ExpressionAttributeValues={':cutoff': cutoff_date},
            Limit=50
        )
        
        patterns = response.get('Items', [])
        
        if not patterns:
            return {
                'total_patterns': 0,
                'pattern_types': {},
                'top_insights': [],
                'recommendations': ['No patterns discovered yet. Upload documents to generate insights.']
            }
        
        # Analyze patterns
        pattern_types = {}
        confidence_scores = []
        top_patterns = []
        
        for pattern in patterns:
            pattern_type = pattern.get('pattern_type', 'unknown')
            pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
            
            confidence = float(pattern.get('confidence_score', 0))
            confidence_scores.append(confidence)
            
            top_patterns.append({
                'description': pattern.get('description', ''),
                'details': pattern.get('details', ''),
                'confidence': confidence,
                'type': pattern_type
            })
        
        # Sort by confidence
        top_patterns.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Generate recommendations
        recommendations = []
        if pattern_types.get('document_content', 0) > 3:
            recommendations.append('Consistent document themes detected - consider creating standardized templates')
        if pattern_types.get('user_queries', 0) > 5:
            recommendations.append('Common query patterns found - consider implementing shortcuts for frequent requests')
        if pattern_types.get('client_behavior', 0) > 2:
            recommendations.append('User behavior patterns identified - optimize features based on usage trends')
        
        return {
            'total_patterns': len(patterns),
            'pattern_types': pattern_types,
            'average_confidence': round(sum(confidence_scores) / len(confidence_scores), 2) if confidence_scores else 0,
            'top_insights': top_patterns[:5],
            'recommendations': recommendations or ['Continue using the system to generate more insights']
        }
        
    except Exception as e:
        logger.error(f"Error getting pattern insights: {str(e)}")
        return {
            'error': str(e),
            'total_patterns': 0,
            'insights': []
        }

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
    
    def __init__(self):
        """Initialize the presentation agent"""
        self.ai_generator = AIPresentationGenerator() if AIPresentationGenerator else None
    
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process presentation generation request"""
        try:
            instructions = request.get('instructions', '')
            template_key = request.get('template_key', 'PUBLIC IP South Plains (1).pptx')
            mode = request.get('mode', 'modify')
            user_id = request.get('user_id', 'anonymous')
            use_ai = request.get('use_ai', True)  # Default to using AI
            
            # Generate unique presentation ID
            presentation_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            logger.info(f"PresentationAgent processing: {presentation_id}")
            logger.info(f"Using AI: {use_ai and self.ai_generator is not None}")
            
            # Log presentation generation event
            log_audit_event(
                user_id,
                'PRESENTATION_GENERATION',
                presentation_id,
                'presentation_creation',
                {
                    'mode': mode,
                    'template': template_key if mode == 'modify' else 'new',
                    'instructions_length': len(instructions)
                }
            )
            
            # Trigger pattern analysis for presentation requests
            trigger_pattern_analysis('presentation_request', {
                'user_id': user_id,
                'mode': mode,
                'instructions_preview': instructions[:100] + '...' if len(instructions) > 100 else instructions
            })
            
            # Always create new presentation based on instructions
            # This ensures each request generates unique content
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
        try:
            # Use AI generator if available and enabled
            if self.ai_generator and instructions:
                logger.info("Using AI presentation generator")
                
                # Generate presentation using AI
                pptx_content = self.ai_generator.generate_presentation(instructions)
                
                # Determine filename based on content
                if "loan portfolio" in instructions.lower():
                    filename = "loan_portfolio_presentation.pptx"
                elif "private equity" in instructions.lower() or "investment committee" in instructions.lower():
                    filename = "pe_investment_committee_deck.pptx"
                elif "debt issuance" in instructions.lower():
                    filename = "debt_issuance_presentation.pptx"
                else:
                    filename = "ai_generated_presentation.pptx"
            else:
                logger.info("Using basic presentation generator")
                pptx_content = create_basic_powerpoint(instructions, timestamp)
                filename = "presentation.pptx"
            
            # Save PowerPoint file to S3
            output_key = f"{presentation_id}/{filename}"
            
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
                'presentation_name': filename,
                'download_url': download_url,
                'status': 'success',
                'mode': 'create',
                'agent': 'presentation',
                'ai_generated': bool(self.ai_generator and instructions)
            }
            
        except Exception as e:
            logger.error(f"Error in _create_presentation: {str(e)}")
            # Fallback to basic presentation if AI fails
            pptx_content = create_basic_powerpoint(instructions, timestamp)
            output_key = f"{presentation_id}/presentation.pptx"
            
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=pptx_content,
                ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            
            download_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': OUTPUT_BUCKET, 'Key': output_key},
                ExpiresIn=3600
            )
            
            return {
                'presentation_id': presentation_id,
                'output_url': f"s3://{OUTPUT_BUCKET}/{output_key}",
                'message': 'Presentation created with basic template (AI generation failed)',
                'presentation_name': 'presentation.pptx',
                'download_url': download_url,
                'status': 'success',
                'mode': 'create',
                'agent': 'presentation',
                'ai_generated': False,
                'error': str(e)
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
                }),
                contentType='application/json'
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
        """Prepare prompt with context from files and knowledge base"""
        # Start with the user's message
        prompt_parts = [message]
        
        # Check if we need to search knowledge base documents
        if self._should_search_knowledge_base(message):
            kb_context = self._search_knowledge_base(message)
            if kb_context:
                prompt_parts.append("\n\n**Relevant information from knowledge base:**")
                prompt_parts.append(kb_context)
        
        # Add context from uploaded files if provided
        if files:
            prompt_parts.append("\n\n**Context from uploaded files:**")
            for file_key in files[:3]:  # Limit to first 3 files
                try:
                    # Download file content from S3
                    file_obj = s3.get_object(Bucket='scribbe-ai-dev-storage', Key=file_key)
                    content = file_obj['Body'].read().decode('utf-8', errors='ignore')
                    filename = file_key.split('/')[-1]
                    prompt_parts.append(f"\n--- {filename} ---\n{content[:2000]}...")
                except Exception as e:
                    logger.error(f"Error reading file {file_key}: {str(e)}")
        
        return "\n".join(prompt_parts)
    
    def _should_search_knowledge_base(self, message: str) -> bool:
        """Determine if we should search the knowledge base"""
        # Keywords that suggest knowledge base search
        search_indicators = [
            'what is', 'who is', 'tell me about', 'explain', 'describe',
            'how does', 'how do', 'when was', 'where is', 'why is',
            'define', 'information about', 'details on', 'facts about'
        ]
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in search_indicators)
    
    def _search_knowledge_base(self, query: str) -> Optional[str]:
        """Search documents in S3 knowledge base"""
        try:
            # List documents in the documents bucket
            response = s3.list_objects_v2(
                Bucket=DOCUMENTS_BUCKET,
                MaxKeys=10  # Limit to recent documents
            )
            
            if 'Contents' not in response:
                return None
            
            relevant_content = []
            
            # Search through documents for relevant content
            for obj in response['Contents']:
                if obj['Size'] > 5000000:  # Skip files larger than 5MB
                    continue
                    
                try:
                    # Download and read document
                    doc_response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=obj['Key'])
                    content = doc_response['Body'].read().decode('utf-8', errors='ignore')
                    
                    # Simple relevance check (could be enhanced with embeddings)
                    if any(word in content.lower() for word in query.lower().split()):
                        doc_name = obj['Key'].split('/')[-1]
                        # Extract relevant snippet
                        snippet = self._extract_relevant_snippet(content, query, max_length=500)
                        if snippet:
                            relevant_content.append(f"**From {doc_name}:**\n{snippet}")
                        
                        if len(relevant_content) >= 3:  # Limit to 3 most relevant snippets
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing document {obj['Key']}: {str(e)}")
                    continue
            
            return "\n\n".join(relevant_content) if relevant_content else None
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return None
    
    def _extract_relevant_snippet(self, content: str, query: str, max_length: int = 500) -> Optional[str]:
        """Extract the most relevant snippet from content based on query"""
        # Simple implementation - find first occurrence of query words
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_position = -1
        for word in query_words:
            position = content_lower.find(word)
            if position != -1 and (best_position == -1 or position < best_position):
                best_position = position
        
        if best_position == -1:
            return None
        
        # Extract snippet around the found position
        start = max(0, best_position - 100)
        end = min(len(content), best_position + max_length)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet

# Document Agent
class DocumentAgent(Agent):
    """Agent for analyzing and extracting information from documents"""
    
    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process document analysis request"""
        try:
            message = request.get('instructions', '')
            files = request.get('files', [])
            user_id = request.get('user_id', 'anonymous')
            
            if not files:
                return {
                    'message': 'Please upload a document to analyze.',
                    'status': 'error',
                    'agent': 'document'
                }
            
            logger.info(f"DocumentAgent analyzing {len(files)} files")
            
            # Log document analysis event
            for file_key in files:
                log_audit_event(
                    user_id,
                    'DOCUMENT_ANALYSIS',
                    file_key,
                    'document_processing',
                    {
                        'filename': file_key.split('/')[-1],
                        'analysis_type': 'ai_analysis'
                    }
                )
            
            # Trigger pattern analysis for document uploads
            trigger_pattern_analysis('document_upload', {
                'user_id': user_id,
                'file_count': len(files),
                'instructions': message[:100] + '...' if len(message) > 100 else message
            })
            
            # Analyze documents using Bedrock
            analysis_prompt = f"""Analyze the following documents and {message}.
            
            Documents:"""
            
            documents_content = []
            for file_key in files:
                try:
                    # Download file content
                    file_obj = s3.get_object(Bucket='scribbe-ai-dev-storage', Key=file_key)
                    content = file_obj['Body'].read().decode('utf-8', errors='ignore')
                    filename = file_key.split('/')[-1]
                    analysis_prompt += f"\n\n--- {filename} ---\n{content[:2000]}"
                    
                    # Store full content for knowledge base
                    documents_content.append({
                        'filename': filename,
                        'content': content,
                        'key': file_key
                    })
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
                }),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            analysis_result = response_body['content'][0]['text']
            
            # Save documents to knowledge base
            saved_documents = []
            if "save" in message.lower() or "knowledge base" in message.lower():
                for doc in documents_content:
                    saved_key = self._save_to_knowledge_base(doc)
                    if saved_key:
                        saved_documents.append(saved_key)
            
            result_message = analysis_result
            if saved_documents:
                result_message += f"\n\n✅ **Saved {len(saved_documents)} document(s) to knowledge base for future queries.**"
            
            return {
                'message': result_message,
                'status': 'success',
                'agent': 'document',
                'files_analyzed': len(files),
                'saved_to_kb': saved_documents
            }
            
        except Exception as e:
            logger.error(f"DocumentAgent error: {str(e)}")
            return {
                'error': 'Failed to analyze documents',
                'message': str(e),
                'agent': 'document'
            }
    
    def _save_to_knowledge_base(self, document: Dict[str, str]) -> Optional[str]:
        """Save document to knowledge base in S3"""
        try:
            timestamp = datetime.utcnow().isoformat()
            # Create a unique key in the documents bucket
            kb_key = f"knowledge-base/{timestamp}_{document['filename']}"
            
            # Save to documents bucket
            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=kb_key,
                Body=document['content'].encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'source': 'document-agent',
                    'original-filename': document['filename'],
                    'indexed-at': timestamp
                }
            )
            
            logger.info(f"Saved document to knowledge base: {kb_key}")
            return kb_key
            
        except Exception as e:
            logger.error(f"Error saving to knowledge base: {str(e)}")
            return None

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
        """Use AI to intelligently determine which agent should handle the request"""
        try:
            # First try quick keyword matching for obvious cases
            lower_instructions = instructions.lower()
            
            # Very obvious presentation keywords
            if any(word in lower_instructions for word in ['slide', 'powerpoint', 'pptx', 'presentation']):
                return 'presentation'
            
            # Use AI for intelligent routing
            routing_prompt = f"""Analyze this user request and determine which specialized agent should handle it.

User Request: "{instructions}"
Has attached files: {"Yes" if files else "No"}

Available agents and their capabilities:
1. presentation - Handles creating/modifying PowerPoint presentations, slides, charts, and visual content
2. document - Specializes in analyzing, extracting information from uploaded documents, PDFs, contracts, reports
3. chat - Handles general questions, conversations, explanations, and knowledge-based queries

Examples:
- "Create a slide about Q2 results" → presentation
- "What is the capital of France?" → chat
- "Analyze this contract for key terms" → document (if file attached)
- "Explain quantum computing" → chat
- "Update slide 23 with new data" → presentation
- "Summarize the attached PDF" → document

Based on the user's request, which agent should handle this? Respond with ONLY one word: presentation, document, or chat."""

            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps({
                    "messages": [{
                        "role": "user",
                        "content": routing_prompt
                    }],
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "anthropic_version": "bedrock-2023-05-31"
                }),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            agent_choice = response_body['content'][0]['text'].strip().lower()
            
            # Validate response
            valid_agents = ['presentation', 'document', 'chat']
            if agent_choice in valid_agents:
                logger.info(f"AI Orchestrator selected: {agent_choice} for request: {instructions[:50]}...")
                return agent_choice
            else:
                logger.warning(f"AI returned invalid agent: {agent_choice}, defaulting to chat")
                return 'chat'
                
        except Exception as e:
            logger.error(f"AI routing failed, falling back to keyword matching: {str(e)}")
            # Fallback to simple keyword matching
            if files and any(keyword in lower_instructions for keyword in ['analyze', 'extract', 'summarize', 'review']):
                return 'document'
            return 'chat'

# Global orchestrator instance
orchestrator = OrchestratorAgent()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Multi-Agent orchestrator Lambda handler.
    Supports both original and LangChain orchestrators.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check HTTP method and path
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        # Handle audit logging endpoint
        if path == '/audit' and http_method == 'POST':
            # Verify user is authenticated (any role can log audit events)
            is_authorized, user_id, user_groups = verify_user_permissions(event, 'ReadOnly')
            if not is_authorized:
                return cors_response(403, {
                    'error': 'Forbidden',
                    'message': 'Authentication required'
                })
            
            # Parse audit event data
            body_str = event.get('body', '{}')
            audit_data = json.loads(body_str)
            
            # Forward to audit logger
            log_audit_event(
                user_id,
                audit_data.get('action', 'UNKNOWN'),
                audit_data.get('resource', ''),
                audit_data.get('eventType', 'user_action'),
                audit_data.get('details', {})
            )
            
            return cors_response(200, {'message': 'Audit event logged'})
        
        # Handle pattern insights endpoint
        if path == '/patterns' and http_method == 'GET':
            # Verify user has at least ReadOnly permission
            is_authorized, user_id, user_groups = verify_user_permissions(event, 'ReadOnly')
            if not is_authorized:
                return cors_response(403, {
                    'error': 'Forbidden',
                    'message': 'You need at least ReadOnly permissions to view patterns'
                })
            
            # Get pattern insights
            insights = get_pattern_insights()
            log_audit_event(user_id, 'VIEW_PATTERNS', 'pattern_insights', 'access')
            
            return cors_response(200, {
                'insights': insights,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Verify user permissions
        if http_method == 'GET':
            # List presentations requires ReadOnly
            is_authorized, user_id, user_groups = verify_user_permissions(event, 'ReadOnly')
            if not is_authorized:
                return cors_response(403, {
                    'error': 'Forbidden',
                    'message': 'You need at least ReadOnly permissions to list presentations'
                })
            # Log audit event
            log_audit_event(user_id, 'LIST_PRESENTATIONS', 'presentations', 'access')
            return list_presentations()
        
        # Parse request for POST
        body_str = event.get('body', '{}')
        if not body_str:
            body_str = '{}'
        body = json.loads(body_str)
        
        # Determine required permission based on request
        instructions = body.get('instructions', '')
        files = body.get('files', [])
        
        # Presentations and file uploads require WriteAccess
        if files or 'presentation' in instructions.lower() or 'slide' in instructions.lower():
            required_permission = 'WriteAccess'
        else:
            required_permission = 'ReadOnly'
        
        # Verify user permissions
        is_authorized, user_id, user_groups = verify_user_permissions(event, required_permission)
        if not is_authorized:
            return cors_response(403, {
                'error': 'Forbidden',
                'message': f'You need {required_permission} permissions for this operation'
            })
        
        # Log audit event for the request
        log_audit_event(
            user_id, 
            'API_REQUEST', 
            'orchestrator',
            'api_call',
            {
                'instructions': instructions[:100] + '...' if len(instructions) > 100 else instructions,
                'has_files': bool(files),
                'groups': user_groups
            }
        )
        
        # Check if we should use LangChain orchestrator
        use_langchain = body.get('use_langchain', False) or os.environ.get('USE_LANGCHAIN', 'false').lower() == 'true'
        
        if use_langchain:
            try:
                # Import and use Simple LangChain orchestrator (with Tavily)
                import simple_langchain_orchestrator
                return simple_langchain_orchestrator.lambda_handler(event, context)
            except ImportError as e:
                logger.warning(f"Simple LangChain orchestrator not available, falling back to original orchestrator: {str(e)}")
        
        # Extract request parameters for original orchestrator
        request = {
            'instructions': body.get('instructions', ''),
            'template_key': body.get('template_key', 'PUBLIC IP South Plains (1).pptx'),
            'document_key': body.get('document_key', ''),
            'files': body.get('files', []),
            'mode': body.get('mode', 'modify'),
            'analyze_structure': body.get('analyze_structure', False),
            'user_id': user_id,  # Pass user_id for audit logging
            'user_groups': user_groups
        }
        
        # Route request through original orchestrator
        response = orchestrator.route_request(request)
        
        # Log successful completion
        log_audit_event(
            user_id,
            'REQUEST_COMPLETED',
            response.get('routed_to', 'unknown'),
            'success',
            {
                'status': response.get('status', 'unknown'),
                'agent': response.get('agent', 'unknown')
            }
        )
        
        # Return CORS-safe response
        return cors_response(200, response)
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        return cors_response(500, {
            'error': 'Internal server error',
            'message': str(e),
            'status': 'error'
        })