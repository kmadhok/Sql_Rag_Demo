# Product Requirement Document: Saved Queries and Dashboard Feature

## Executive Summary

This PRD outlines the implementation of a saved queries system and dashboard feature for the SQL RAG application. Users will be able to save SQL queries and their execution results to a local folder, then display these results as modular dashboard widgets on a dedicated dashboard page.

### Project Overview
- **Feature**: Saved Queries with Persistent Local Storage and Dashboard Display
- **Type**: Brownfield Enhancement (building on existing SQL execution functionality)
- **Priority**: High - adds significant value to power users
- **Timeline**: 3-4 weeks for robust MVP implementation

## Problem Statement

Currently, the SQL RAG application can execute SQL queries on BigQuery and display results, but:
1. Query results are ephemeral (stored only in session state)
2. Users cannot save frequently used queries for later use
3. No dashboard exists for viewing multiple query results simultaneously
4. No persistence mechanism exists for query history or results

## Solution Architecture

### High-Level Design
```
Query Execution → Save to Local Folder → Dashboard Display
    ↓                ↓                    ↓
Streamlit/FastAPI  JSON/CSV Files      Modular Widgets
```

### Technical Architecture

#### 1. Saved Queries Storage
- **Location**: Local folder outside application directory (`~/.sql_rag_saved_queries/`)
- **Format**: JSON files for metadata, CSV for result data
- **Structure**: 
  - `queries/` - SQL query definitions and metadata
  - `results/` - Query execution results (CSV format)
  - `dashboards/` - Dashboard configurations

#### 2. Dashboard Implementation
- **New Page**: `/dashboard` route in both Streamlit and React frontends
- **Widget System**: Modular components for different table types
- **Layout**: Grid-based with lazy loading and caching

## User Stories

### Epic: Query Persistence

**US-1: Save SQL Query**
- **As a** power user
- **I want to** save a successfully executed SQL query to a local folder
- **So that** I can reuse it later without re-generating

**Acceptance Criteria:**
- [ ] Save button appears after successful query execution
- [ ] Query metadata (SQL, description, timestamp) saved to JSON
- [ ] Execution results saved to CSV file with validation
- [ ] Success confirmation message displayed
- [ ] Saved queries appear in a dedicated management interface
- [ ] Atomic write operations prevent data corruption

**US-2: Load Saved Query**
- **As a** returning user
- **I want to** load a previously saved query
- **So that** I can execute it again or modify it

**Acceptance Criteria:**
- [ ] Saved queries list displays in query search interface
- [ ] Clicking a saved query loads it into the execution interface
- [ ] Option to execute immediately or edit first
- [ ] Query history shows last execution timestamp
- [ ] Error handling for corrupted or missing files

### Epic: Dashboard Management

**US-3: Create Dashboard Widget**
- **As a** data analyst
- **I want to** add a saved query result as a dashboard widget
- **So that** I can monitor key metrics over time

**Acceptance Criteria:**
- [ ] "Add to Dashboard" button on saved query results
- [ ] Widget configuration (title, refresh interval, display options)
- [ ] Widget appears on dashboard page with lazy loading
- [ ] Widget displays current query results with caching
- [ ] Background refresh options for real-time updates

**US-4: Manage Dashboard Layout**
- **As a** dashboard user
- **I want to** arrange widgets in a customizable layout
- **So that** I can prioritize important information

**Acceptance Criteria:**
- [ ] Drag-and-drop widget repositioning
- [ ] Resizable widgets with aspect ratio preservation
- [ ] Save layout configuration with versioning
- [ ] Multiple dashboard tabs support
- [ ] Graceful degradation if some widgets fail to load

## Technical Requirements

### Backend Requirements

#### 1. Enhanced Saved Query Service
```python
class SavedQueryService:
    def save_query(query_metadata: EnhancedQueryMetadata, results: pd.DataFrame) -> str
    def load_query(query_id: str) -> Tuple[EnhancedQueryMetadata, pd.DataFrame]
    def list_queries() -> List[EnhancedQueryMetadata]
    def delete_query(query_id: str) -> bool
    def validate_query_integrity(query_id: str) -> bool
    def search_queries(query: str) -> List[EnhancedQueryMetadata]
```

#### 2. Enhanced Query Metadata Schema
```python
@dataclass
class EnhancedQueryMetadata:
    # Core fields
    id: str
    name: str
    sql: str
    description: str
    
    # Security & Validation
    sql_hash: str  # SHA256 for change detection
    user_id: str
    organization_id: Optional[str]
    
    # Tracking
    created_at: datetime
    updated_at: datetime
    last_executed: Optional[datetime]
    execution_count: int
    
    # Performance
    avg_execution_time: float
    avg_cost_usd: Optional[float]
    
    # Result metadata
    result_schema: Dict[str, str]
    estimated_row_count: int
    
    # Classification
    tags: List[str]
    category: Optional[str]
    is_public: bool = False
    version: int = 1
```

#### 3. Robust Dashboard Service
```python
class DashboardService:
    def create_widget(query_id: str, config: WidgetConfig) -> str
    def get_dashboard() -> Dashboard
    def update_widget_layout(layout: List[WidgetPosition])
    def refresh_widget(widget_id: str) -> pd.DataFrame
    def validate_widget_config(config: WidgetConfig) -> bool
    def get_widget_performance(widget_id: str) -> WidgetPerformance
```

#### 4. Abstract Storage Layer
```python
class StorageBackend(ABC):
    @abstractmethod
    def save_query(self, query_id: str, metadata: dict, results: pd.DataFrame) -> bool
    @abstractmethod
    def load_query(self, query_id: str) -> Tuple[dict, pd.DataFrame]
    @abstractmethod
    def atomic_write(self, path: Path, data: Any) -> bool
    @abstractmethod
    def validate_path(self, path: str) -> bool

class LocalFileStorage(StorageBackend):
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.lock = threading.Lock()
```

### Frontend Requirements

#### 1. Streamlit Implementation
- New page: `pages/4_📊_Dashboard.py`
- Saved queries sidebar with search functionality
- Dashboard widget components with lazy loading
- Error handling for failed widget loads

#### 2. React Implementation
- New route: `/dashboard`
- Dashboard page component with virtual grid
- Widget components with background refresh
- Performance monitoring for widget loading

### Storage Requirements

#### 1. Secure File Structure
```
~/.sql_rag_saved_queries/
├── queries/
│   ├── {query_id}.json          # Query metadata (validated)
│   ├── {query_id}.tmp           # Temporary files for atomic writes
│   └── index.json               # Query catalog with checksums
├── results/
│   └── {query_id}_{timestamp}.csv  # Result data with validation
└── dashboards/
    ├── default.json             # Dashboard configuration
    └── backups/                 # Versioned backups
```

#### 2. Enhanced Data Formats
- **Query Metadata JSON**: Enhanced schema with validation
- **Results CSV**: Validated CSV with size limits
- **Dashboard Config JSON**: Versioned configuration with backups

## Security Requirements

### 1. Input Validation
- **SQL Injection Prevention**: Validate and sanitize all SQL inputs
- **File Path Security**: Prevent path traversal attacks
- **Content Validation**: Scan for malicious content in saved data

### 2. Access Control
- **User Isolation**: Separate storage per user where applicable
- **Permission Validation**: Verify write permissions before file operations
- **Data Encryption**: Optional encryption for sensitive query results

### 3. Data Integrity
- **Atomic Operations**: Prevent partial writes and data corruption
- **Checksum Validation**: Verify file integrity on load
- **Backup Mechanisms**: Automatic backups for critical data

## Performance Requirements

### 1. Response Time Targets
- **Dashboard Load**: < 3 seconds for initial render
- **Widget Refresh**: < 2 seconds for individual widgets
- **Query Save/Load**: < 1 second for typical operations

### 2. Resource Limits
- **Memory Usage**: < 500MB for dashboard with 10 widgets
- **Result Size**: Maximum 50MB per query result
- **Concurrent Operations**: Support 5+ simultaneous users

### 3. Optimization Strategies
- **Lazy Loading**: Load widget data on-demand
- **Result Caching**: 30-minute TTL for query results
- **Background Processing**: Async refresh for dashboard widgets

## Success Metrics

### Key Performance Indicators (KPIs)
- **Query Save Rate**: Percentage of executed queries that get saved
- **Dashboard Usage**: Number of active dashboard users per week
- **Query Reuse Rate**: Percentage of saved queries executed more than once
- **User Satisfaction**: Survey feedback on dashboard usefulness
- **Performance Metrics**: 95th percentile load times under targets

### Quality Metrics
- **Data Integrity**: 99.9% successful save/load operations
- **Error Rate**: < 1% failed widget loads
- **Uptime**: 99.5% availability for dashboard features
- **Security**: Zero security incidents related to saved queries

## Dependencies and Risks

### Dependencies
1. **Existing SQL Execution**: Requires stable BigQuery executor
2. **Frontend Framework**: Both Streamlit and React implementations needed
3. **File System Access**: Local file permissions and cross-platform compatibility
4. **Security Libraries**: Input validation and path security utilities

### Risks and Mitigations

#### Technical Risks
- **Risk**: File system permissions issues
  - **Mitigation**: Graceful fallback to application directory with validation
- **Risk**: Large result sets impacting performance
  - **Mitigation**: Streaming results, pagination, and size limits
- **Risk**: Cross-platform file path differences
  - **Mitigation**: Use pathlib with comprehensive testing
- **Risk**: Data corruption during concurrent access
  - **Mitigation**: File locking and atomic write operations

#### Security Risks
- **Risk**: SQL injection in saved queries
  - **Mitigation**: Input validation and query sanitization
- **Risk**: Path traversal attacks
  - **Mitigation**: Strict path validation and realpath checking
- **Risk**: Unauthorized data access
  - **Mitigation**: User isolation and permission checks

#### User Experience Risks
- **Risk**: Complex dashboard configuration
  - **Mitigation**: Simple default layouts and guided setup
- **Risk**: Data staleness in dashboard widgets
  - **Mitigation**: Clear refresh indicators and background updates
- **Risk**: Performance issues with many widgets
  - **Mitigation**: Lazy loading and performance monitoring

## Implementation Timeline

### Phase 0: Foundation (1 week)
- [ ] Implement abstract storage layer with atomic operations
- [ ] Create comprehensive error handling framework
- [ ] Develop security validation utilities
- [ ] Establish performance monitoring infrastructure

### Phase 1: Core Infrastructure (Week 2)
- [ ] Implement SavedQueryService with enhanced metadata
- [ ] Create robust file persistence system with validation
- [ ] Add save/load functionality to query execution
- [ ] Basic saved queries list interface with search

### Phase 2: Dashboard MVP (Week 3)
- [ ] Create dashboard page skeleton with lazy loading
- [ ] Implement basic widget system with caching
- [ ] Add query results to dashboard with background refresh
- [ ] Simple grid layout system with error handling

### Phase 3: Enhancement (Week 4)
- [ ] Advanced dashboard features (tabs, layouts)
- [ ] Widget configuration options and performance optimization
- [ ] User testing and refinement based on feedback
- [ ] Security audit and performance tuning

### Stretch Goals
- [ ] Drag-and-drop widget arrangement
- [ ] Scheduled query execution
- [ ] Dashboard sharing capabilities
- [ ] Advanced visualization options
- [ ] Multi-user collaboration features

## Technical Constraints

### Platform Constraints
- **Streamlit**: Enhanced session state synchronization required
- **React/FastAPI**: Backend coordination for multi-user scenarios
- **File System**: Cross-platform compatibility with security validation

### Performance Constraints
- **Result Size**: Limit individual result sets to 50MB with streaming
- **Dashboard Load**: Maximum 15 widgets with lazy loading
- **Refresh Rate**: Configurable refresh intervals with background processing

### Security Constraints
- **Local Storage**: Enhanced security validation for all file operations
- **File Access**: Comprehensive permission checking and user isolation
- **Data Exposure**: Privacy controls and optional encryption

## Testing Strategy

### Unit Tests
- SavedQueryService save/load operations with edge cases
- File format validation and corruption handling
- Security validation for inputs and file paths
- Performance testing for large result sets

### Integration Tests
- End-to-end query save/load workflow with concurrency
- Dashboard widget creation and display under load
- Cross-platform file path handling validation
- Error recovery and data corruption scenarios

### Security Tests
- SQL injection prevention validation
- Path traversal attack prevention
- Permission escalation testing
- Data integrity validation

### Performance Tests
- Load testing for dashboard with multiple widgets
- Stress testing for large result sets
- Concurrency testing for multiple users
- Memory usage profiling and optimization

### User Acceptance Testing
- Query saving workflow with error scenarios
- Dashboard usability under various conditions
- Performance with large result sets and many widgets
- Security validation from user perspective

## Monitoring and Observability

### Metrics Collection
- **Performance Metrics**: Load times, refresh intervals, memory usage
- **Usage Metrics**: Query save rates, dashboard activity, widget usage
- **Error Metrics**: Failed operations, corruption incidents, security events
- **Business Metrics**: User satisfaction, feature adoption rates

### Alerting
- **Performance Alerts**: Dashboard load times exceeding thresholds
- **Error Alerts**: High failure rates for save/load operations
- **Security Alerts**: Suspicious file access patterns
- **Capacity Alerts**: Storage space limitations approaching

## Documentation Requirements

### User Documentation
- How to save and manage queries with security best practices
- Dashboard setup and customization with performance tips
- Troubleshooting common issues and error recovery
- Security guidelines for sensitive data handling

### Technical Documentation
- File format specifications with validation rules
- API endpoints for saved queries with security considerations
- Widget development guide with performance guidelines
- Deployment guide for multi-user environments

### Operational Documentation
- Monitoring and alerting configuration
- Backup and recovery procedures
- Performance tuning guidelines
- Security audit checklist

## Conclusion

This enhanced feature will significantly improve the SQL RAG application by providing robust persistent storage for valuable queries and a high-performance dashboard for monitoring key metrics. The implementation follows a phased approach with strong focus on security, performance, and reliability.

The local file persistence approach ensures the feature works independently of the application deployment method, while the abstract storage layer provides flexibility for future cloud or database storage options. The comprehensive security and performance considerations make this suitable for enterprise-grade deployments.