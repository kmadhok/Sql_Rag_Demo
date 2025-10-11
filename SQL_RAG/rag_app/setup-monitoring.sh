#!/bin/bash

# SQL RAG Application - Monitoring and Logging Setup Script
# This script sets up comprehensive monitoring, alerting, and logging for Cloud Run deployment

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="sql-rag-app"
NOTIFICATION_EMAIL=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud CLI (gcloud) is not installed."
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 >/dev/null 2>&1; then
        print_error "Not authenticated with Google Cloud. Run: gcloud auth login"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup project configuration
setup_project() {
    if [ -z "$PROJECT_ID" ]; then
        CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
        
        if [ -z "$CURRENT_PROJECT" ]; then
            print_error "No Google Cloud project is set."
            echo "Please run: gcloud config set project YOUR_PROJECT_ID"
            exit 1
        else
            PROJECT_ID="$CURRENT_PROJECT"
            print_status "Using current project: $PROJECT_ID"
        fi
    else
        print_status "Using configured project: $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
}

# Function to enable required APIs
enable_monitoring_apis() {
    print_status "Enabling monitoring and logging APIs..."
    
    gcloud services enable \
        monitoring.googleapis.com \
        logging.googleapis.com \
        bigquery.googleapis.com \
        storage.googleapis.com \
        cloudasset.googleapis.com
    
    print_success "APIs enabled successfully"
}

# Function to create BigQuery datasets
create_bigquery_datasets() {
    print_status "Creating BigQuery datasets for log storage..."
    
    # Create error logs dataset
    if ! bq ls -d "${PROJECT_ID}:sql_rag_logs" >/dev/null 2>&1; then
        bq mk \
            --dataset \
            --description="SQL RAG Application Error Logs" \
            --default_table_expiration=7776000 \
            --location=US \
            --label=application:sql-rag \
            --label=environment:production \
            --label=data_type:logs \
            "${PROJECT_ID}:sql_rag_logs"
        print_success "Created sql_rag_logs dataset"
    else
        print_warning "Dataset sql_rag_logs already exists"
    fi
    
    # Create metrics dataset
    if ! bq ls -d "${PROJECT_ID}:sql_rag_metrics" >/dev/null 2>&1; then
        bq mk \
            --dataset \
            --description="SQL RAG Application Metrics" \
            --default_table_expiration=15552000 \
            --location=US \
            --label=application:sql-rag \
            --label=environment:production \
            --label=data_type:metrics \
            "${PROJECT_ID}:sql_rag_metrics"
        print_success "Created sql_rag_metrics dataset"
    else
        print_warning "Dataset sql_rag_metrics already exists"
    fi
}

# Function to create Cloud Storage bucket for security logs
create_security_logs_bucket() {
    print_status "Creating Cloud Storage bucket for security logs..."
    
    BUCKET_NAME="${PROJECT_ID}-security-logs"
    
    if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
        gsutil mb \
            -c COLDLINE \
            -l US \
            "gs://${BUCKET_NAME}"
        
        # Set lifecycle policy for 7-year retention
        cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
      }
    ]
  }
}
EOF
        gsutil lifecycle set lifecycle.json "gs://${BUCKET_NAME}"
        rm lifecycle.json
        
        # Set labels
        gsutil label ch -l application:sql-rag "gs://${BUCKET_NAME}"
        gsutil label ch -l environment:production "gs://${BUCKET_NAME}"
        gsutil label ch -l data_type:security-logs "gs://${BUCKET_NAME}"
        
        print_success "Created security logs bucket: ${BUCKET_NAME}"
    else
        print_warning "Bucket ${BUCKET_NAME} already exists"
    fi
}

# Function to create log sinks
create_log_sinks() {
    print_status "Creating log sinks..."
    
    # Error logs sink to BigQuery
    if ! gcloud logging sinks describe sql-rag-error-logs >/dev/null 2>&1; then
        gcloud logging sinks create sql-rag-error-logs \
            "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/sql_rag_logs" \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
(severity>=ERROR OR jsonPayload.level="ERROR")'
        print_success "Created error logs sink"
    else
        print_warning "Error logs sink already exists"
    fi
    
    # Metrics sink to BigQuery
    if ! gcloud logging sinks describe sql-rag-metrics-logs >/dev/null 2>&1; then
        gcloud logging sinks create sql-rag-metrics-logs \
            "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/sql_rag_metrics" \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
(jsonPayload.type="metrics" OR jsonPayload.event_type="performance" OR jsonPayload.event_type="usage")'
        print_success "Created metrics logs sink"
    else
        print_warning "Metrics logs sink already exists"
    fi
    
    # Security logs sink to Cloud Storage
    if ! gcloud logging sinks describe sql-rag-security-logs >/dev/null 2>&1; then
        gcloud logging sinks create sql-rag-security-logs \
            "storage.googleapis.com/${PROJECT_ID}-security-logs" \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
(jsonPayload.event_type="security" OR jsonPayload.type="auth" OR jsonPayload.unauthorized=true)'
        print_success "Created security logs sink"
    else
        print_warning "Security logs sink already exists"
    fi
}

# Function to create log exclusions
create_log_exclusions() {
    print_status "Creating log exclusions to reduce noise..."
    
    # Exclude health check logs
    if ! gcloud logging sinks describe exclude-health-checks >/dev/null 2>&1; then
        gcloud logging exclusions create exclude-health-checks \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
httpRequest.requestUrl:"/_stcore/health"
httpRequest.status=200' \
            --description="Exclude successful health check requests"
        print_success "Created health check exclusion"
    else
        print_warning "Health check exclusion already exists"
    fi
    
    # Exclude static asset logs
    if ! gcloud logging sinks describe exclude-static-assets >/dev/null 2>&1; then
        gcloud logging exclusions create exclude-static-assets \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
httpRequest.requestUrl:("/static/" OR "/favicon.ico" OR "/_stcore/static/")
httpRequest.status=200' \
            --description="Exclude successful static asset requests"
        print_success "Created static assets exclusion"
    else
        print_warning "Static assets exclusion already exists"
    fi
}

# Function to create log-based metrics
create_log_metrics() {
    print_status "Creating log-based metrics..."
    
    # Error rate metric
    if ! gcloud logging metrics describe sql_rag_error_rate >/dev/null 2>&1; then
        gcloud logging metrics create sql_rag_error_rate \
            --description="Count of error-level log entries for SQL RAG application" \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
severity>=ERROR'
        print_success "Created error rate metric"
    else
        print_warning "Error rate metric already exists"
    fi
    
    # OpenAI API calls metric
    if ! gcloud logging metrics describe sql_rag_openai_api_calls >/dev/null 2>&1; then
        gcloud logging metrics create sql_rag_openai_api_calls \
            --description="Count of OpenAI API calls" \
            --log-filter='resource.type="cloud_run_revision"
resource.labels.service_name="'${SERVICE_NAME}'"
jsonPayload.event_type="openai_api_call"' \
            --label-extractors='model=EXTRACT(jsonPayload.model),status=EXTRACT(jsonPayload.status)'
        print_success "Created OpenAI API calls metric"
    else
        print_warning "OpenAI API calls metric already exists"
    fi
}

# Function to create notification channel
create_notification_channel() {
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        print_status "Creating notification channel for email: $NOTIFICATION_EMAIL"
        
        # Create email notification channel
        CHANNEL_ID=$(gcloud alpha monitoring channels create \
            --display-name="SQL RAG Admin Email" \
            --type="email" \
            --channel-labels="email_address=${NOTIFICATION_EMAIL}" \
            --description="Email notifications for SQL RAG application alerts" \
            --format="value(name)")
        
        if [ -n "$CHANNEL_ID" ]; then
            print_success "Created notification channel: $CHANNEL_ID"
            echo "$CHANNEL_ID" > .notification_channel_id
        else
            print_warning "Failed to create notification channel"
        fi
    else
        print_warning "No notification email provided. Skipping notification channel creation."
        echo "To add email notifications later, set NOTIFICATION_EMAIL and run this script again."
    fi
}

# Function to create alert policies
create_alert_policies() {
    print_status "Creating alert policies..."
    
    # High error rate alert
    if ! gcloud alpha monitoring policies list --filter='displayName:"SQL RAG High Error Rate"' --format="value(name)" | head -n1 >/dev/null 2>&1; then
        cat > error_rate_policy.yaml << EOF
displayName: "SQL RAG High Error Rate"
documentation:
  content: |
    This alert fires when the SQL RAG application experiences a high error rate.
    
    Troubleshooting steps:
    1. Check Cloud Run logs
    2. Verify API key configuration
    3. Check OpenAI and Gemini API status
    4. Review recent deployments
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        resource.labels.service_name="${SERVICE_NAME}"
        metric.type="run.googleapis.com/request_count"
        metric.labels.response_code_class!="2xx"
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: 300s
alertStrategy:
  autoClose: 604800s
EOF
        gcloud alpha monitoring policies create --policy-from-file=error_rate_policy.yaml
        rm error_rate_policy.yaml
        print_success "Created error rate alert policy"
    else
        print_warning "Error rate alert policy already exists"
    fi
    
    # High latency alert
    if ! gcloud alpha monitoring policies list --filter='displayName:"SQL RAG High Response Time"' --format="value(name)" | head -n1 >/dev/null 2>&1; then
        cat > latency_policy.yaml << EOF
displayName: "SQL RAG High Response Time"
documentation:
  content: |
    This alert fires when response time is consistently high.
    
    Common causes:
    1. Cold starts
    2. OpenAI API latency
    3. Large embedding operations
    4. Memory pressure
conditions:
  - displayName: "95th percentile latency > 5 seconds"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        resource.labels.service_name="${SERVICE_NAME}"
        metric.type="run.googleapis.com/request_latencies"
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5000
      duration: 300s
alertStrategy:
  autoClose: 604800s
EOF
        gcloud alpha monitoring policies create --policy-from-file=latency_policy.yaml
        rm latency_policy.yaml
        print_success "Created latency alert policy"
    else
        print_warning "Latency alert policy already exists"
    fi
}

# Function to create uptime check
create_uptime_check() {
    print_status "Creating uptime check..."
    
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -n "$SERVICE_URL" ]; then
        HOST=$(echo "$SERVICE_URL" | sed 's|https://||' | sed 's|http://||')
        
        if ! gcloud monitoring uptime list --filter='displayName:"SQL RAG Health Check"' --format="value(name)" | head -n1 >/dev/null 2>&1; then
            gcloud monitoring uptime create \
                --display-name="SQL RAG Health Check" \
                --http-check-path="/_stcore/health" \
                --hostname="$HOST" \
                --timeout=10 \
                --period=60 \
                --content-match="ok"
            print_success "Created uptime check for: $SERVICE_URL"
        else
            print_warning "Uptime check already exists"
        fi
    else
        print_warning "Service not deployed yet. Uptime check will need to be created after deployment."
    fi
}

# Function to set up monitoring dashboard
create_dashboard() {
    print_status "Creating monitoring dashboard..."
    
    # Note: Dashboard creation via gcloud is limited
    # Provide instructions for manual setup
    cat > dashboard_config.json << EOF
{
  "displayName": "SQL RAG Application Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\\"cloud_run_revision\\" resource.labels.service_name=\\"${SERVICE_NAME}\\" metric.type=\\"run.googleapis.com/request_count\\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
    
    print_success "Dashboard configuration saved to dashboard_config.json"
    print_status "To create the dashboard:"
    echo "1. Go to Google Cloud Console > Monitoring > Dashboards"
    echo "2. Click 'Create Dashboard'"
    echo "3. Import the configuration from dashboard_config.json"
}

# Function to grant necessary permissions
grant_permissions() {
    print_status "Granting necessary permissions..."
    
    # Get the Logs Writer service account for sinks
    LOGS_WRITER_SA=$(gcloud logging sinks describe sql-rag-error-logs --format="value(writerIdentity)" 2>/dev/null || echo "")
    
    if [ -n "$LOGS_WRITER_SA" ]; then
        # Grant BigQuery Data Editor role for log sinks
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="$LOGS_WRITER_SA" \
            --role="roles/bigquery.dataEditor" >/dev/null 2>&1 || true
        
        # Grant Storage Object Creator role for security logs
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="$LOGS_WRITER_SA" \
            --role="roles/storage.objectCreator" >/dev/null 2>&1 || true
        
        print_success "Granted necessary permissions"
    else
        print_warning "Could not find logs writer service account. Permissions may need to be set manually."
    fi
}

# Main function
main() {
    echo "🔍 SQL RAG Application - Monitoring & Logging Setup"
    echo "================================================="
    echo
    
    # Get notification email if not set
    if [ -z "$NOTIFICATION_EMAIL" ]; then
        read -p "Enter email for alert notifications (optional): " NOTIFICATION_EMAIL
    fi
    
    check_prerequisites
    setup_project
    enable_monitoring_apis
    create_bigquery_datasets
    create_security_logs_bucket
    create_log_sinks
    create_log_exclusions
    create_log_metrics
    create_notification_channel
    create_alert_policies
    create_uptime_check
    create_dashboard
    grant_permissions
    
    echo
    print_success "Monitoring and logging setup completed!"
    echo
    echo "📊 Access your monitoring at:"
    echo "   https://console.cloud.google.com/monitoring/dashboards?project=${PROJECT_ID}"
    echo
    echo "📋 View logs at:"
    echo "   https://console.cloud.google.com/logs/query?project=${PROJECT_ID}"
    echo
    echo "🔔 Manage alerts at:"
    echo "   https://console.cloud.google.com/monitoring/alerting?project=${PROJECT_ID}"
    echo
    echo "📈 Query metrics in BigQuery:"
    echo "   https://console.cloud.google.com/bigquery?project=${PROJECT_ID}"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "SQL RAG Application Monitoring Setup Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h         Show this help message"
        echo "  --project-id       Set Google Cloud project ID"
        echo "  --service-name     Set Cloud Run service name"
        echo "  --notification-email Set email for alert notifications"
        echo
        exit 0
        ;;
    --project-id)
        PROJECT_ID="$2"
        shift 2
        ;;
    --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
    --notification-email)
        NOTIFICATION_EMAIL="$2"
        shift 2
        ;;
    "")
        # No arguments, proceed with setup
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run the main setup
main