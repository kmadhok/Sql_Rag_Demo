# SQL RAG Testing Suite

This directory contains comprehensive tests for the modular SQL RAG application. The tests are designed to be simple, reliable, and gradually increase in complexity.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and basic fixtures
├── mock_helpers.py          # Mock classes for Streamlit and dependencies
├── fixtures.py              # Sample data and configuration fixtures
├── run_tests.py            # Test runner script
├── README.md               # This file
├── unit/                   # Unit tests
│   ├── __init__.py
│   ├── test_utils.py       # Tests for utility functions
│   ├── test_page_classes.py # Basic page class tests
│   ├── test_search_page.py # SearchPage specific tests
│   └── test_catalog_page.py # CatalogPage specific tests
└── integration/            # Integration tests
    ├── __init__.py
    └── test_page_integration.py # Component interaction tests
```

## Test Philosophy

### Phase 1: Simple Unit Tests ✅
- **Focus**: Individual functions and class methods
- **Dependencies**: Minimal - mostly standard library
- **Mocking**: Light mocking of external dependencies
- **Examples**: Utility functions, validation logic, data parsing

### Phase 2: Component Tests ✅
- **Focus**: Page components with mocked Streamlit
- **Dependencies**: Mock Streamlit components and session state
- **Mocking**: Comprehensive mocking of UI and external services
- **Examples**: Configuration rendering, search logic, pagination

### Phase 3: Integration Tests ✅
- **Focus**: Interaction between components
- **Dependencies**: Coordinated mocks across multiple components
- **Mocking**: Realistic mock scenarios simulating real workflows
- **Examples**: Search workflow, page navigation, error handling

### Phase 4: End-to-End Tests (Future)
- **Focus**: Complete user workflows
- **Dependencies**: Real or near-real external services
- **Mocking**: Minimal - mostly for external APIs
- **Examples**: Full app execution, real data processing

## Running Tests

### Quick Start
```bash
# Run all tests
python tests/run_tests.py

# Run only unit tests
python tests/run_tests.py unit

# Run only integration tests
python tests/run_tests.py integration

# Run with verbose output
python tests/run_tests.py all -v
```

### Using pytest directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_utils.py

# Run specific test class
pytest tests/unit/test_utils.py::TestEstimateTokenCount

# Run specific test method
pytest tests/unit/test_utils.py::TestEstimateTokenCount::test_empty_string

# Run with coverage
pytest tests/ --cov=modular --cov-report=term-missing

# Run with verbose output
pytest tests/ -v
```

## Test Categories

### Unit Tests (`tests/unit/`)

#### `test_utils.py`
Tests for utility functions in `modular.utils`:
- Token estimation and context utilization
- Data validation and safe value extraction
- Pagination calculations
- Cost formatting and calculation
- Text processing and agent type extraction

#### `test_page_classes.py`
Basic tests for page class instantiation:
- Page class creation without external dependencies
- Required method existence
- Basic error handling

#### `test_search_page.py`
SearchPage specific functionality:
- Configuration rendering with different options
- Query card display with parsed/raw data
- Search results display and context utilization
- Input validation and instructions

#### `test_catalog_page.py`
CatalogPage specific functionality:
- Analytics loading and display
- Search functionality with different data types
- Pagination controls and navigation
- Query card display with complex join data

### Integration Tests (`tests/integration/`)

#### `test_page_integration.py`
Component interaction scenarios:
- Complete search workflow from input to results
- Catalog browsing with analytics and pagination
- Chat page initialization and error handling
- Page routing and state management
- End-to-end user workflows

## Mock Strategy

### Streamlit Components
- **MockStreamlitComponents**: Comprehensive mocking of all Streamlit UI elements
- **Configurable responses**: Set return values for inputs and session state
- **Context manager support**: Proper handling of Streamlit containers and layouts

### Application Components
- **MockSessionManager**: Simulates session state management
- **MockVectorStoreManager**: Mocks vector store operations
- **MockRAGEngine**: Simulates RAG query processing
- **MockDocuments**: Creates mock document objects for testing

### Data Fixtures
- **Sample query data**: Various sizes and formats for different test scenarios
- **Analytics data**: Complete analytics objects for catalog testing
- **Configuration objects**: Different search and page configurations
- **Mock responses**: Realistic RAG engine responses with token usage

## Test Data

### Query Data Types
- **Minimal**: Basic 2-query dataset for simple tests
- **Basic**: 5-query dataset with tables and joins
- **Parsed**: Pre-processed data with parsed tables/joins
- **Search**: Optimized for search functionality testing
- **Large**: 100+ queries for pagination testing

### Analytics Types
- **Comprehensive**: Full analytics with all join types and relationships
- **Minimal**: Basic analytics for simple scenarios
- **No joins**: Analytics for datasets without joins

## Dependencies

### Required for Testing
```bash
pip install pytest
pip install pytest-mock  # For easier mocking
```

### Optional but Recommended
```bash
pip install pytest-cov   # For coverage reporting
pip install pytest-xdist # For parallel test execution
```

### Installation
```bash
# Install test dependencies
pip install -r requirements.txt

# Or install testing extras if configured
pip install -e .[testing]
```

## Writing New Tests

### Guidelines
1. **Start simple**: Test individual functions before complex interactions
2. **Mock external dependencies**: Don't rely on real Streamlit, APIs, or files
3. **Use fixtures**: Leverage existing fixtures for consistent test data
4. **Test error cases**: Include tests for error handling and edge cases
5. **Clear naming**: Use descriptive test names that explain what's being tested

### Example Test Structure
```python
class TestNewFeature:
    """Test new feature functionality"""
    
    def test_basic_functionality(self):
        """Test basic feature operation"""
        # Arrange
        mock_data = get_sample_query_data('basic')
        
        # Act
        result = process_feature(mock_data)
        
        # Assert
        assert result is not None
        assert len(result) > 0
    
    def test_error_handling(self):
        """Test feature error handling"""
        # Test with invalid input
        with pytest.raises(ValueError):
            process_feature(None)
```

### Using Fixtures
```python
def test_with_fixtures(sample_query_data):
    """Test using pytest fixtures"""
    result = process_data(sample_query_data)
    assert result is not None

def test_with_custom_fixtures():
    """Test using custom fixtures"""
    data = get_sample_query_data('parsed')
    config = get_search_config('advanced')
    
    result = search_function(data, config)
    assert len(result) > 0
```

## Troubleshooting

### Common Issues

#### Import Errors
```python
# Add project root to path in test files
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

#### Streamlit Mocking Issues
```python
# Use context managers for complex mocking
with patch.multiple(
    'modular.page_modules.search_page',
    st=mock_st,
    session_manager=mock_session_manager
):
    # Test code here
    pass
```

#### Session State Issues
```python
# Configure session state before testing
mock_st.configure_session_state({
    'key': 'value',
    'selected_index': 'test_index'
})
```

### Performance Tips
- Use `pytest-xdist` for parallel execution: `pytest -n auto`
- Run specific test categories during development
- Use `--lf` flag to run only last failed tests
- Use `--ff` flag to run failed tests first

## Contributing

When adding new features to the application:

1. **Write tests first** (TDD approach when possible)
2. **Start with unit tests** for new utility functions
3. **Add component tests** for UI functionality
4. **Include integration tests** for complex workflows
5. **Update fixtures** if new data formats are needed
6. **Document test scenarios** in docstrings

## Future Improvements

- **End-to-end tests** with real Streamlit app execution
- **Performance tests** for large datasets
- **Visual regression tests** for UI consistency
- **API integration tests** with real external services
- **Test data generation** for more diverse scenarios