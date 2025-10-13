"""
Minimal Single Slide Extractor
Creates a minimal presentation with only one slide
"""

import zipfile
import io
import xml.etree.ElementTree as ET
import re
from typing import Set, Dict
import logging

logger = logging.getLogger(__name__)

class MinimalSlideExtractor:
    def __init__(self, template_bytes: bytes):
        self.template_bytes = template_bytes
        
    def extract_slide(self, slide_number: int) -> bytes:
        """Extract a single slide and create minimal presentation"""
        
        with zipfile.ZipFile(io.BytesIO(self.template_bytes), 'r') as template_zip:
            # Find required files
            slide_filename = f'ppt/slides/slide{slide_number}.xml'
            slide_rels_filename = f'ppt/slides/_rels/slide{slide_number}.xml.rels'
            
            if slide_filename not in template_zip.namelist():
                raise ValueError(f"Slide {slide_number} not found")
            
            # Read the slide to find required resources
            slide_content = template_zip.read(slide_filename)
            slide_rels_content = None
            if slide_rels_filename in template_zip.namelist():
                slide_rels_content = template_zip.read(slide_rels_filename)
                
            # Find required resources from slide relationships
            required_resources = self._find_required_resources(slide_rels_content) if slide_rels_content else set()
            logger.info(f"Found {len(required_resources)} required resources: {required_resources}")
            
            # Create new minimal presentation
            output_buffer = io.BytesIO()
            
            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                # Copy minimal required files
                minimal_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'docProps/app.xml',
                    'docProps/core.xml',
                ]
                
                for filename in minimal_files:
                    if filename in template_zip.namelist():
                        new_zip.writestr(filename, template_zip.read(filename))
                
                # Copy slide as slide1
                new_zip.writestr('ppt/slides/slide1.xml', slide_content)
                
                # Copy slide rels if exists
                if slide_rels_content:
                    # Update rels to point to new locations
                    updated_rels = self._update_slide_rels(slide_rels_content)
                    new_zip.writestr('ppt/slides/_rels/slide1.xml.rels', updated_rels)
                
                # Copy required layout
                layout_match = re.search(r'slideLayout(\\d+)\\.xml', str(slide_rels_content))
                if layout_match:
                    layout_num = layout_match.group(1)
                    layout_file = f'ppt/slideLayouts/slideLayout{layout_num}.xml'
                    if layout_file in template_zip.namelist():
                        new_zip.writestr(layout_file, template_zip.read(layout_file))
                        
                        # Copy layout rels
                        layout_rels = f'ppt/slideLayouts/_rels/slideLayout{layout_num}.xml.rels'
                        if layout_rels in template_zip.namelist():
                            new_zip.writestr(layout_rels, template_zip.read(layout_rels))
                
                # Copy required master
                master_file = 'ppt/slideMasters/slideMaster1.xml'
                if master_file in template_zip.namelist():
                    new_zip.writestr(master_file, template_zip.read(master_file))
                    
                    master_rels = 'ppt/slideMasters/_rels/slideMaster1.xml.rels'
                    if master_rels in template_zip.namelist():
                        new_zip.writestr(master_rels, template_zip.read(master_rels))
                
                # Copy theme
                theme_files = [f for f in template_zip.namelist() if f.startswith('ppt/theme/')]
                for theme_file in theme_files[:1]:  # Just copy first theme
                    new_zip.writestr(theme_file, template_zip.read(theme_file))
                
                # Copy only required media/charts
                for resource in required_resources:
                    resource_path = f'ppt/{resource}'
                    if resource_path in template_zip.namelist():
                        new_zip.writestr(resource_path, template_zip.read(resource_path))
                        logger.info(f"Copied resource: {resource_path}")
                    else:
                        logger.warning(f"Resource not found: {resource_path}")
                
                # Also check for chart .rels files
                if any('charts/' in r for r in required_resources):
                    chart_rels_dir = 'ppt/charts/_rels/'
                    for f in template_zip.namelist():
                        if f.startswith(chart_rels_dir):
                            new_zip.writestr(f, template_zip.read(f))
                            logger.info(f"Copied chart rels: {f}")
                
                # Create minimal presentation.xml
                pres_xml = self._create_minimal_presentation_xml()
                new_zip.writestr('ppt/presentation.xml', pres_xml)
                
                # Create minimal presentation.xml.rels
                pres_rels = self._create_minimal_presentation_rels()
                new_zip.writestr('ppt/_rels/presentation.xml.rels', pres_rels)
                
                # Copy viewProps and presProps if they exist
                for props_file in ['ppt/viewProps.xml', 'ppt/presProps.xml']:
                    if props_file in template_zip.namelist():
                        new_zip.writestr(props_file, template_zip.read(props_file))
            
            output_buffer.seek(0)
            return output_buffer.getvalue()
    
    def _find_required_resources(self, rels_content: bytes) -> Set[str]:
        """Find media and chart resources required by the slide"""
        resources = set()
        
        # Parse relationships
        root = ET.fromstring(rels_content)
        ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
        
        for rel in root.findall('.//r:Relationship', ns):
            target = rel.get('Target', '')
            rel_type = rel.get('Type', '')
            
            # Get media and charts
            if '../media/' in target or '../charts/' in target:
                # Convert relative to ppt/... path
                resources.add(target.replace('../', ''))
            # Also check by relationship type
            elif 'chart' in rel_type:
                resources.add(target.replace('../', ''))
                logger.info(f"Found chart relationship: {target}")
                
        return resources
    
    def _update_slide_rels(self, rels_content: bytes) -> bytes:
        """Update slide relationships for new structure"""
        # For now, just return as-is
        # In production, you might need to update paths
        return rels_content
    
    def _create_minimal_presentation_xml(self) -> bytes:
        """Create minimal presentation.xml with one slide"""
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" 
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" 
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId1"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId2"/>
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''
        return xml.encode('utf-8')
    
    def _create_minimal_presentation_rels(self) -> bytes:
        """Create minimal presentation relationships"""
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
    <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps" Target="viewProps.xml"/>
    <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps" Target="presProps.xml"/>
</Relationships>'''
        return xml.encode('utf-8')


def extract_single_slide_minimal(template_bytes: bytes, slide_number: int) -> bytes:
    """Helper function for minimal extraction"""
    extractor = MinimalSlideExtractor(template_bytes)
    return extractor.extract_slide(slide_number)