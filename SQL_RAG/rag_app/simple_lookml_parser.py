#!/usr/bin/env python3
"""
Simple LookML Parser for SQL RAG Integration
Focused on extracting explores, joins, and generating safe-join maps quickly and reliably.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimpleJoin:
    """Simple join representation"""
    name: str
    sql_on: str = ""
    relationship: str = "many_to_one"
    join_type: str = "left_outer"
    required_joins: List[str] = field(default_factory=list)


@dataclass
class SimpleExplore:
    """Simple explore representation"""
    name: str
    label: str = ""
    description: str = ""
    joins: List[SimpleJoin] = field(default_factory=list)
    base_table: str = ""


class SimpleLookMLParser:
    """
    Simple, fast LookML parser focused on explores and joins
    Uses regex patterns for reliable parsing
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single LookML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if self.verbose:
                logger.info(f"Parsing: {file_path}")
            
            result = {
                'file_path': str(file_path),
                'connection': self._extract_connection(content),
                'label': self._extract_label(content),
                'constants': self._extract_constants(content),
                'explores': self._extract_explores(content)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return {'file_path': str(file_path), 'error': str(e)}
    
    def parse_directory(self, dir_path: Path) -> List[Dict[str, Any]]:
        """Parse all .lkml files in directory"""
        dir_path = Path(dir_path)
        models = []
        
        for file_path in dir_path.rglob("*.lkml"):
            model = self.parse_file(file_path)
            if 'error' not in model:
                models.append(model)
        
        if self.verbose:
            logger.info(f"Parsed {len(models)} LookML files")
        
        return models
    
    def _extract_connection(self, content: str) -> str:
        """Extract connection name"""
        match = re.search(r'connection:\s*["\']([^"\']+)["\']', content)
        return match.group(1) if match else ""
    
    def _extract_label(self, content: str) -> str:
        """Extract label"""
        match = re.search(r'label:\s*["\']([^"\']+)["\']', content)
        return match.group(1) if match else ""
    
    def _extract_constants(self, content: str) -> Dict[str, str]:
        """Extract constants"""
        constants = {}
        pattern = r'constant:\s*(\w+)\s*\{\s*value:\s*["\']([^"\']+)["\']\s*\}'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        for name, value in matches:
            constants[name] = value
        
        return constants
    
    def _extract_explores(self, content: str) -> List[Dict[str, Any]]:
        """Extract explore definitions"""
        explores = []
        
        # Find explore blocks with proper nested brace handling
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for explore start
            if line.startswith('explore:') and '{' in line:
                # Extract explore name
                explore_match = re.search(r'explore:\s*(\w+)', line)
                if explore_match:
                    explore_name = explore_match.group(1)
                    
                    # Extract the entire explore block
                    explore_content, next_i = self._extract_block_content(lines, i)
                    
                    if explore_content:
                        explore = self._parse_explore(explore_name, explore_content)
                        if explore:
                            explores.append(explore)
                    
                    i = next_i
                else:
                    i += 1
            else:
                i += 1
        
        return explores
    
    def _extract_block_content(self, lines: List[str], start_i: int) -> tuple[str, int]:
        """Extract content of a block (between braces) and return content + next index"""
        brace_count = 0
        block_lines = []
        i = start_i
        
        while i < len(lines):
            line = lines[i]
            
            # Count braces
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            block_lines.append(line)
            i += 1
            
            # If we've closed all braces, we're done
            if brace_count == 0:
                break
        
        return '\n'.join(block_lines), i
    
    def _parse_explore(self, explore_name: str, explore_content: str) -> Optional[Dict[str, Any]]:
        """Parse a single explore"""
        try:
            # Extract basic properties
            label = self._extract_property(explore_content, 'label')
            description = self._extract_property(explore_content, 'description')
            
            # Extract joins
            joins = self._extract_joins(explore_content)
            
            explore = {
                'name': explore_name,
                'label': label or explore_name,
                'description': description,
                'joins': joins,
                'join_count': len(joins)
            }
            
            return explore
            
        except Exception as e:
            logger.error(f"Failed to parse explore {explore_name}: {e}")
            return None
    
    def _extract_property(self, content: str, property_name: str) -> str:
        """Extract a simple property value"""
        pattern = rf'{property_name}:\s*["\']([^"\']+)["\']'
        match = re.search(pattern, content)
        return match.group(1) if match else ""
    
    def _extract_joins(self, explore_content: str) -> List[Dict[str, Any]]:
        """Extract join definitions from explore"""
        joins = []
        
        # Parse joins using line-by-line approach for better handling
        lines = explore_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for join start
            if line.startswith('join:') and '{' in line:
                # Extract join name
                join_match = re.search(r'join:\s*(\w+)', line)
                if join_match:
                    join_name = join_match.group(1)
                    
                    # Extract the join block content
                    join_content, next_i = self._extract_block_content(lines, i)
                    
                    if join_content:
                        join = self._parse_join(join_name, join_content)
                        if join:
                            joins.append(join)
                    
                    i = next_i
                else:
                    i += 1
            else:
                i += 1
        
        return joins
    
    def _parse_join(self, join_name: str, join_content: str) -> Optional[Dict[str, Any]]:
        """Parse a single join"""
        try:
            # Extract join properties
            sql_on = self._extract_sql_on(join_content)
            relationship = self._extract_property(join_content, 'relationship') or "many_to_one"
            join_type = self._extract_property(join_content, 'type') or "left_outer"
            required_joins = self._extract_required_joins(join_content)
            
            join = {
                'name': join_name,
                'sql_on': sql_on,
                'relationship': relationship,
                'join_type': join_type,
                'required_joins': required_joins
            }
            
            return join
            
        except Exception as e:
            logger.error(f"Failed to parse join {join_name}: {e}")
            return None
    
    def _extract_sql_on(self, join_content: str) -> str:
        """Extract sql_on condition"""
        # Handle both quoted and unquoted sql_on
        patterns = [
            r'sql_on:\s*["\']([^"\']+)["\']',  # Quoted
            r'sql_on:\s*([^;]+);;',            # Unquoted with ;;
            r'sql_on:\s*([^}\n]+)',            # Simple unquoted
        ]
        
        for pattern in patterns:
            match = re.search(pattern, join_content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_required_joins(self, join_content: str) -> List[str]:
        """Extract required_joins array"""
        pattern = r'required_joins:\s*\[([^\]]+)\]'
        match = re.search(pattern, join_content)
        
        if match:
            # Parse the array content
            array_content = match.group(1)
            # Split by comma and clean up
            items = [item.strip().strip('"\'') for item in array_content.split(',')]
            return [item for item in items if item]
        
        return []
    
    def generate_safe_join_map(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate safe-join map from parsed models"""
        if self.verbose:
            logger.info("Generating safe-join map")
        
        safe_join_map = {
            'project': '',
            'explores': {},
            'join_graph': {},
            'metadata': {
                'total_explores': 0,
                'total_joins': 0,
                'files_processed': len(models)
            }
        }
        
        total_joins = 0
        
        for model in models:
            # Set project name from first model with label
            if not safe_join_map['project'] and model.get('label'):
                safe_join_map['project'] = model['label']
            
            # Process explores
            for explore in model.get('explores', []):
                explore_name = explore['name']
                
                # Create explore entry
                explore_info = {
                    'label': explore.get('label', explore_name),
                    'description': explore.get('description', ''),
                    'base_table': explore_name,  # Simplified - using explore name as base table
                    'joins': {},
                    'file_path': model['file_path']
                }
                
                # Add joins
                for join in explore.get('joins', []):
                    join_info = {
                        'sql_on': join['sql_on'],
                        'relationship': join['relationship'],
                        'join_type': join['join_type'],
                        'required_joins': join.get('required_joins', []),
                        'required': bool(join.get('required_joins'))
                    }
                    
                    explore_info['joins'][join['name']] = join_info
                    total_joins += 1
                    
                    # Build join graph
                    if explore_name not in safe_join_map['join_graph']:
                        safe_join_map['join_graph'][explore_name] = []
                    safe_join_map['join_graph'][explore_name].append(join['name'])
                
                safe_join_map['explores'][explore_name] = explore_info
        
        # Update metadata
        safe_join_map['metadata']['total_explores'] = len(safe_join_map['explores'])
        safe_join_map['metadata']['total_joins'] = total_joins
        
        if self.verbose:
            logger.info(f"Generated safe-join map: {len(safe_join_map['explores'])} explores, {total_joins} joins")
        
        return safe_join_map
    
    def create_embedding_documents(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create embedding documents from models"""
        if self.verbose:
            logger.info("Creating embedding documents")
        
        documents = []
        
        for model in models:
            for explore in model.get('explores', []):
                # Create explore document
                doc = self._create_explore_document(explore, model)
                documents.append(doc)
                
                # Create individual join documents
                for join in explore.get('joins', []):
                    join_doc = self._create_join_document(join, explore, model)
                    documents.append(join_doc)
        
        if self.verbose:
            logger.info(f"Created {len(documents)} embedding documents")
        
        return documents
    
    def _create_explore_document(self, explore: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """Create document for explore"""
        content_parts = [
            f"Explore: {explore['name']}"
        ]
        
        if explore.get('label'):
            content_parts.append(f"Label: {explore['label']}")
        
        if explore.get('description'):
            content_parts.append(f"Description: {explore['description']}")
        
        # Add join information
        joins = explore.get('joins', [])
        if joins:
            content_parts.append(f"Joins ({len(joins)}):")
            for join in joins:
                join_desc = f"  - {join['name']} ({join['relationship']}): {join['sql_on']}"
                content_parts.append(join_desc)
        
        # Add table list
        tables = [explore['name']] + [join['name'] for join in joins]
        content_parts.append(f"Tables: {', '.join(tables)}")
        
        content = "\n".join(content_parts)
        
        return {
            'page_content': content,
            'metadata': {
                'source': 'lookml',
                'type': 'explore',
                'explore_name': explore['name'],
                'label': explore.get('label', ''),
                'base_table': explore['name'],
                'joins': [join['name'] for join in joins],
                'joined_tables': tables,
                'join_count': len(joins),
                'file_path': model['file_path']
            }
        }
    
    def _create_join_document(self, join: Dict[str, Any], explore: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """Create document for join"""
        content = f"""Join: {explore['name']} → {join['name']}
Relationship: {join['relationship']}
Join Type: {join['join_type']}
SQL Condition: {join['sql_on']}
Required: {bool(join.get('required_joins'))}
"""
        
        if join.get('required_joins'):
            content += f"Required Joins: {', '.join(join['required_joins'])}\n"
        
        return {
            'page_content': content,
            'metadata': {
                'source': 'lookml',
                'type': 'join',
                'explore_name': explore['name'],
                'join_name': join['name'],
                'left_table': explore['name'],
                'right_table': join['name'],
                'relationship': join['relationship'],
                'join_type': join['join_type'],
                'sql_on': join['sql_on'],
                'file_path': model['file_path']
            }
        }


def main():
    """Test the simple parser"""
    print("🔧 Testing Simple LookML Parser")
    print("=" * 50)
    
    parser = SimpleLookMLParser(verbose=True)
    
    # Test directory parsing
    lookml_dir = Path("lookml_data")
    if lookml_dir.exists():
        models = parser.parse_directory(lookml_dir)
        
        print(f"\n📊 Parsing Results:")
        print(f"   - Parsed {len(models)} models")
        
        # Show sample model info
        for model in models[:3]:
            print(f"\n   📄 {Path(model['file_path']).name}:")
            print(f"      - Label: {model.get('label', 'N/A')}")
            print(f"      - Connection: {model.get('connection', 'N/A')}")
            print(f"      - Explores: {len(model.get('explores', []))}")
            
            # Show explores
            for explore in model.get('explores', [])[:2]:
                print(f"        🔍 {explore['name']} ({len(explore.get('joins', []))} joins)")
        
        # Generate safe-join map
        if models:
            safe_join_map = parser.generate_safe_join_map(models)
            
            print(f"\n🔗 Safe-Join Map:")
            print(f"   - Project: {safe_join_map['project']}")
            print(f"   - Explores: {safe_join_map['metadata']['total_explores']}")
            print(f"   - Joins: {safe_join_map['metadata']['total_joins']}")
            
            # Save safe-join map
            output_file = Path("lookml_safe_join_map.json")
            with open(output_file, 'w') as f:
                json.dump(safe_join_map, f, indent=2)
            print(f"   - Saved to: {output_file}")
            
            # Create embedding documents
            documents = parser.create_embedding_documents(models)
            print(f"\n📄 Created {len(documents)} embedding documents")
            
            # Show sample documents
            for i, doc in enumerate(documents[:3]):
                print(f"\n   📄 Document {i+1} ({doc['metadata']['type']}):")
                print(f"      - Content: {doc['page_content'][:100]}...")
                print(f"      - Metadata: {list(doc['metadata'].keys())}")
        
        print(f"\n✅ Simple LookML parser test completed!")
        
    else:
        print(f"❌ LookML directory not found: {lookml_dir}")


if __name__ == "__main__":
    main()