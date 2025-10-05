#!/usr/bin/env python3
"""
Test script for LookML parser with debugging
"""

import sys
from pathlib import Path
from lookml_parser import LookMLParser, LookMLLexer

def test_lexer():
    """Test the lexer with a simple LookML snippet"""
    print("🔧 Testing LookML Lexer")
    print("=" * 40)
    
    sample_lookml = """
connection: "bigquery_conn"
label: "TheLook"

explore: users {
  label: "Ecommerce Core"
  
  join: orders {
    type: left_outer
    relationship: one_to_many
    sql_on: ${orders.user_id} = ${users.id} ;;
  }
}
"""
    
    lexer = LookMLLexer()
    tokens = lexer.tokenize(sample_lookml, Path("test.lkml"))
    
    print(f"Generated {len(tokens)} tokens:")
    for i, token in enumerate(tokens[:10]):  # Show first 10
        print(f"  {i}: {token}")
    
    return tokens

def test_single_file():
    """Test parsing a single LookML file"""
    print("\n🔧 Testing Single File Parsing")
    print("=" * 40)
    
    lookml_file = Path("lookml_data/model/manifest.lkml")
    
    if not lookml_file.exists():
        print(f"❌ File not found: {lookml_file}")
        return None
    
    parser = LookMLParser(verbose=True)
    model = parser.parse_file(lookml_file)
    
    if model:
        print(f"✅ Successfully parsed: {lookml_file}")
        print(f"   - Connection: {model.connection}")
        print(f"   - Label: {model.label}")
        print(f"   - Views: {len(model.views)}")
        print(f"   - Explores: {len(model.explores)}")
        print(f"   - Constants: {len(model.constants)}")
        
        # Show constants if any
        if model.constants:
            print(f"   - Constants: {model.constants}")
        
        return model
    else:
        print(f"❌ Failed to parse: {lookml_file}")
        return None

def test_explore_file():
    """Test parsing an explore/model file"""
    print("\n🔧 Testing Explore File Parsing")
    print("=" * 40)
    
    lookml_file = Path("lookml_data/model/thelook.model.lkml")
    
    if not lookml_file.exists():
        print(f"❌ File not found: {lookml_file}")
        return None
    
    parser = LookMLParser(verbose=True)
    model = parser.parse_file(lookml_file)
    
    if model:
        print(f"✅ Successfully parsed: {lookml_file}")
        print(f"   - Connection: {model.connection}")
        print(f"   - Label: {model.label}")
        print(f"   - Views: {len(model.views)}")
        print(f"   - Explores: {len(model.explores)}")
        
        # Show explores
        for explore in model.explores:
            print(f"\n   📈 Explore: {explore.name}")
            print(f"      - Label: {explore.label}")
            print(f"      - Joins: {len(explore.joins)}")
            
            # Show joins
            for join in explore.joins[:3]:  # First 3 joins
                print(f"        → {join.name} ({join.relationship})")
        
        return model
    else:
        print(f"❌ Failed to parse: {lookml_file}")
        return None

def test_view_file():
    """Test parsing a view file"""
    print("\n🔧 Testing View File Parsing")
    print("=" * 40)
    
    lookml_file = Path("lookml_data/views/users.view.lkml")
    
    if not lookml_file.exists():
        print(f"❌ File not found: {lookml_file}")
        return None
    
    parser = LookMLParser(verbose=True)
    model = parser.parse_file(lookml_file)
    
    if model:
        print(f"✅ Successfully parsed: {lookml_file}")
        print(f"   - Views: {len(model.views)}")
        
        # Show view details
        for view in model.views:
            print(f"\n   📋 View: {view.name}")
            print(f"      - SQL Table: {view.sql_table_name}")
            print(f"      - Dimensions: {len(view.dimensions)}")
            print(f"      - Measures: {len(view.measures)}")
            
            # Show sample dimensions
            for dim in view.dimensions[:3]:
                print(f"        📊 {dim.name} ({dim.data_type})")
            
            # Show sample measures
            for measure in view.measures[:3]:
                print(f"        📈 {measure.name} ({measure.data_type})")
        
        return model
    else:
        print(f"❌ Failed to parse: {lookml_file}")
        return None

def main():
    """Main test function"""
    print("🚀 LookML Parser Test Suite")
    print("=" * 60)
    
    # Test 1: Lexer
    try:
        tokens = test_lexer()
        print("✅ Lexer test passed")
    except Exception as e:
        print(f"❌ Lexer test failed: {e}")
        return
    
    # Test 2: Simple file (manifest)
    try:
        manifest_model = test_single_file()
        if manifest_model:
            print("✅ Manifest parsing passed")
        else:
            print("❌ Manifest parsing failed")
    except Exception as e:
        print(f"❌ Manifest parsing failed: {e}")
        return
    
    # Test 3: View file
    try:
        view_model = test_view_file()
        if view_model:
            print("✅ View parsing passed")
        else:
            print("❌ View parsing failed")
    except Exception as e:
        print(f"❌ View parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Explore file  
    try:
        explore_model = test_explore_file()
        if explore_model:
            print("✅ Explore parsing passed")
        else:
            print("❌ Explore parsing failed")
    except Exception as e:
        print(f"❌ Explore parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n🎉 All tests completed!")

if __name__ == "__main__":
    main()