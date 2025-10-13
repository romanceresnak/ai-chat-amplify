#!/usr/bin/env python3
"""
Test script for South Plains Financial slides generation
"""

import json
from ai_presentation_generator_enhanced import AIPresentationGenerator

def test_south_plains_slides():
    """Test generating South Plains Financial slides"""
    
    # Initialize generator
    generator = AIPresentationGenerator()
    
    # Test Slide 23 generation
    slide_23_prompt = """
    Create a professional corporate slide titled "Loan Portfolio" with a bar and line combo chart 
    labeled Total Loans Held for Investment ($ in Millions) showing loan balances 
    ($1,936M 2Q'19, $1,963M 3Q'19, $2,144M 4Q'19, $2,109M 1Q'20, $2,332M 2Q'20) as red bars, 
    yield percentages (5.90%, 5.91%, 5.79%, 5.76%, 5.26%) as a black line, 
    and yield with PPP (5.06% in 2Q'20) as a dashed gray line, with a legend at the bottom, 
    and a right-hand section titled "2Q'20 Highlights" listing: 
    total loan increase of $229.9M vs. 1Q'20, growth from $215.3M PPP loans and 
    $34.7M seasonal agriculture loans, partial offset from $24.4M pay-downs in 
    non-residential consumer and direct energy loans, over 2,000 PPP loans closed, 
    and 2Q'20 yield of 5.26% (down 50 bps vs. 1Q'20 excluding PPP), 
    styled with red accents, company logo in top right, gray footer bar with 
    South Plains Financial, Inc., and a clean modern design.
    
    Also create Slide 24: donut chart showing loan portfolio composition 
    (Commercial Real Estate 28%, Commercial – General 27%, Commercial – Specialized 14%, 
    1–4 Family Residential 15%, Auto Loans 9%, Construction 4%, Other Consumer 3%), 
    center text inside the donut reading Net Loans – 2Q'20: $2.3 Billion
    """
    
    print("Testing South Plains slide generation...")
    
    try:
        # Generate presentation
        pptx_bytes = generator.generate_presentation(slide_23_prompt)
        
        # Save to file for testing
        with open("south_plains_test.pptx", "wb") as f:
            f.write(pptx_bytes)
        
        print("✅ Successfully generated South Plains slides!")
        print("   Output saved to: south_plains_test.pptx")
        
        # Test PDF parsing (if a financial report is available)
        test_pdf_path = "path/to/financial_report.pdf"  # Update with actual path
        financial_data = generator.parse_financial_report(test_pdf_path)
        
        if financial_data:
            print(f"✅ Successfully parsed financial data: {json.dumps(financial_data, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error generating slides: {e}")
        import traceback
        traceback.print_exc()

def test_specific_slides():
    """Test generating specific slide numbers"""
    
    generator = AIPresentationGenerator()
    
    slide_prompts = [
        {
            'slide_number': 23,
            'title': 'Loan Portfolio',
            'type': 'bar_line_combo'
        },
        {
            'slide_number': 24,
            'title': 'Loan Portfolio',
            'type': 'donut_chart'
        },
        {
            'slide_number': 26,
            'title': 'Loan Portfolio',
            'type': 'bar_line_combo'
        }
    ]
    
    print("\nTesting specific slide generation...")
    
    try:
        pptx_bytes = generator.generate_south_plains_slides(slide_prompts)
        
        with open("south_plains_specific_slides.pptx", "wb") as f:
            f.write(pptx_bytes)
        
        print("✅ Successfully generated specific slides!")
        print("   Output saved to: south_plains_specific_slides.pptx")
        
    except Exception as e:
        print(f"❌ Error generating specific slides: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("South Plains Financial Slide Generator Test")
    print("=" * 50)
    
    # Test full prompt parsing
    test_south_plains_slides()
    
    # Test specific slide generation
    test_specific_slides()
    
    print("\nTest completed!")