"""
Test script to debug python-pptx imports in Lambda
"""
import sys
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def test_imports():
    """Test all imports and log detailed information"""
    
    # Log Python path
    logger.info(f"Python path: {sys.path}")
    
    # Log environment variables
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Try importing python-pptx
    try:
        import pptx
        logger.info(f"Successfully imported pptx from: {pptx.__file__}")
        
        from pptx import Presentation
        logger.info("Successfully imported Presentation")
        
        from pptx.util import Inches, Pt
        logger.info("Successfully imported Inches, Pt")
        
        from pptx.chart.data import ChartData
        logger.info("Successfully imported ChartData")
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import python-pptx: {e}")
        
        # Try to find pptx in common locations
        possible_paths = [
            '/opt/python/lib/python3.11/site-packages',
            '/var/runtime',
            '/var/lang/lib/python3.11/site-packages'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Directory exists: {path}")
                try:
                    contents = os.listdir(path)
                    pptx_related = [item for item in contents if 'pptx' in item.lower()]
                    if pptx_related:
                        logger.info(f"Found pptx-related items in {path}: {pptx_related}")
                    else:
                        logger.info(f"No pptx-related items in {path}")
                except Exception as e:
                    logger.error(f"Error listing {path}: {e}")
            else:
                logger.info(f"Directory does not exist: {path}")
        
        return False

def lambda_handler(event, context):
    """Lambda handler for testing imports"""
    logger.info("Starting import test")
    
    success = test_imports()
    
    return {
        'statusCode': 200,
        'body': {
            'success': success,
            'message': 'Import test completed'
        }
    }

if __name__ == "__main__":
    test_imports()