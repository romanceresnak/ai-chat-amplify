#!/usr/bin/env python3
"""
Test script to invoke the Lambda function to generate the Loan Portfolio slide
"""

import json
import boto3
import base64
from datetime import datetime

# Initialize AWS clients
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')

def create_loan_portfolio_content():
    """
    Create the content structure for Loan Portfolio slide
    """
    return {
        "slides": [
            {
                "slide_number": 1,
                "slide_type": "chart",
                "title": "Loan Portfolio",
                "highlights_title": "2Q'20 Highlights",
                "highlights": [
                    "Total loan increase of $229.9M vs. 1Q'20",
                    "Growth from $215.3M PPP loans and $34.7M seasonal agriculture loans", 
                    "Partial offset from $24.4M pay-downs in non-residential consumer and direct energy loans",
                    "Over 2,000 PPP loans closed",
                    "2Q'20 yield of 5.26% (down 50 bps vs. 1Q'20 excluding PPP)"
                ],
                "charts": [
                    {
                        "chart_type": "combo",
                        "title": "Total Loans Held for Investment ($ in Millions)",
                        "data": {
                            "categories": ["2Q'19", "3Q'19", "4Q'19", "1Q'20", "2Q'20"],
                            "bar_series": [
                                {
                                    "name": "Total Loans",
                                    "values": [1936, 1963, 2144, 2109, 2332]
                                }
                            ],
                            "line_series": [
                                {
                                    "name": "Yield %",
                                    "values": [5.90, 5.91, 5.79, 5.76, 5.26]
                                },
                                {
                                    "name": "Yield with PPP",
                                    "values": [None, None, None, None, 5.06]
                                }
                            ]
                        },
                        "style": {
                            "series_colors": [
                                {"r": 192, "g": 0, "b": 0},  # Red for bars
                                {"r": 0, "g": 0, "b": 0},     # Black for yield line
                                {"r": 128, "g": 128, "b": 128} # Gray for PPP line
                            ],
                            "line_styles": [
                                {"dashed": False},
                                {"dashed": True}
                            ]
                        }
                    }
                ],
                "style": {
                    "primary_color": {"r": 192, "g": 0, "b": 0},
                    "secondary_color": {"r": 128, "g": 128, "b": 128},
                    "footer_text": "South Plains Financial, Inc."
                }
            }
        ],
        "metadata": {
            "title": "Loan Portfolio Presentation",
            "description": "Q2 2020 Loan Portfolio Analysis"
        }
    }

def upload_template():
    """
    Create and upload a basic PowerPoint template
    """
    # For simplicity, we'll use the Lambda's built-in template capabilities
    # by providing an empty template key
    return "default"

def invoke_template_processor(presentation_content, output_key):
    """
    Invoke the template processor Lambda function
    """
    payload = {
        "template_key": "default",
        "presentation_content": presentation_content,
        "output_key": output_key
    }
    
    response = lambda_client.invoke(
        FunctionName="scribbe-ai-dev-template-processor",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    return result

def main():
    """
    Main function to generate and upload the Loan Portfolio slide
    """
    print("🚀 Generating Loan Portfolio slide using Lambda function...")
    
    try:
        # Create presentation content
        presentation_content = create_loan_portfolio_content()
        
        # Generate output key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_key = f"loan_portfolio/presentation_{timestamp}.pptx"
        
        # Invoke Lambda function
        print("📤 Invoking template processor Lambda...")
        result = invoke_template_processor(presentation_content, output_key)
        
        if result.get('statusCode') == 200:
            print(f"✅ Slide successfully generated!")
            print(f"   Bucket: scribbe-ai-dev-output")
            print(f"   Key: {output_key}")
            print(f"   URL: s3://scribbe-ai-dev-output/{output_key}")
            
            # Generate presigned URL
            try:
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': 'scribbe-ai-dev-output', 'Key': output_key},
                    ExpiresIn=3600
                )
                print(f"\n📥 Download URL (valid for 1 hour):")
                print(f"   {presigned_url}")
            except Exception as e:
                print(f"Could not generate presigned URL: {e}")
        else:
            print(f"❌ Error generating slide: {result}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()