#!/bin/bash

# SQL RAG Application - Local Development Setup Script
# This script sets up the local development environment

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check Python version
check_python() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed."
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version="3.11"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        print_success "Python $python_version detected (>= $required_version)"
    else
        print_warning "Python $python_version detected. Python 3.11+ recommended for best performance."
    fi
}

# Function to create virtual environment
create_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Recreate virtual environment? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            print_status "Using existing virtual environment"
            return
        fi
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created"
}

# Function to activate virtual environment and install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    
    print_success "Dependencies installed successfully"
}

# Function to setup environment variables
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
        else
            cat > .env << EOF
# SQL RAG Application Environment Configuration

# ===== REQUIRED API KEYS =====
# OpenAI API Key (for embeddings) - Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Google Gemini API Key (for chat) - Get from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here

# ===== EMBEDDING CONFIGURATION =====
# Embedding provider: "openai" (default) or "ollama" (legacy)
EMBEDDINGS_PROVIDER=openai

# OpenAI embedding model (if using OpenAI)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Ollama embedding model (if using Ollama)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ===== STREAMLIT CONFIGURATION =====
# Streamlit server settings
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# ===== APPLICATION SETTINGS =====
# Environment mode
ENVIRONMENT=development
EOF
            print_success "Created .env file with default configuration"
        fi
        
        print_warning "Please edit .env file and add your API keys:"
        echo "  - OPENAI_API_KEY (get from: https://platform.openai.com/api-keys)"
        echo "  - GEMINI_API_KEY (get from: https://makersuite.google.com/app/apikey)"
    else
        print_warning ".env file already exists"
    fi
}

# Function to check API keys
check_api_keys() {
    print_status "Checking API key configuration..."
    
    # Source the .env file
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Check OpenAI API key
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
        print_warning "OpenAI API key not configured in .env file"
        echo "  Get your key from: https://platform.openai.com/api-keys"
    else
        print_success "OpenAI API key configured"
    fi
    
    # Check Gemini API key
    if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your-gemini-api-key-here" ]; then
        print_warning "Gemini API key not configured in .env file"
        echo "  Get your key from: https://makersuite.google.com/app/apikey"
    else
        print_success "Gemini API key configured"
    fi
}

# Function to generate embeddings
generate_embeddings() {
    print_status "Generating vector embeddings..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if sample data exists
    if [ ! -f "sample_queries_with_metadata.csv" ]; then
        print_error "sample_queries_with_metadata.csv not found"
        echo "Please ensure the sample data file is in the current directory"
        return 1
    fi
    
    # Generate embeddings
    python3 data/standalone_embedding_generator.py \
        --csv "sample_queries_with_metadata.csv" \
        --schema "sample_queries_metadata_schema.csv"
    
    print_success "Vector embeddings generated"
}

# Function to generate analytics cache
generate_analytics() {
    print_status "Generating analytics cache..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Generate analytics
    python3 data/catalog_analytics_generator.py \
        --csv "sample_queries_with_metadata.csv"
    
    print_success "Analytics cache generated"
}

# Function to run validation
run_validation() {
    print_status "Running setup validation..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run validation
    if [ -f "validate_setup.py" ]; then
        python3 validate_setup.py
    else
        print_warning "validate_setup.py not found, skipping validation"
    fi
}

# Function to test OpenAI embeddings
test_openai() {
    print_status "Testing OpenAI embeddings integration..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Test OpenAI
    if [ -f "test_openai_embeddings.py" ]; then
        python3 test_openai_embeddings.py
    else
        print_warning "test_openai_embeddings.py not found, skipping test"
    fi
}

# Function to start the application
start_app() {
    print_status "Starting the SQL RAG application..."
    echo
    print_success "Setup completed! Starting Streamlit application..."
    echo
    echo "🌐 The application will open in your browser at: http://localhost:8501"
    echo "🔄 Use Ctrl+C to stop the application"
    echo
    
    # Activate virtual environment and start app
    source venv/bin/activate
    streamlit run app.py
}

# Main setup function
main() {
    echo "🛠️  SQL RAG Application - Local Development Setup"
    echo "================================================"
    echo
    
    check_python
    create_venv
    install_dependencies
    setup_environment
    check_api_keys
    
    # Ask if user wants to generate embeddings
    echo
    read -p "Generate vector embeddings? (required for first setup) (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        generate_embeddings
        generate_analytics
    fi
    
    # Ask if user wants to run validation
    echo
    read -p "Run setup validation? (recommended) (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_validation
        test_openai
    fi
    
    # Ask if user wants to start the app
    echo
    read -p "Start the application now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_app
    else
        print_success "Setup completed!"
        echo
        echo "To start the application later, run:"
        echo "  source venv/bin/activate"
        echo "  streamlit run app.py"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "SQL RAG Application Local Setup Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h         Show this help message"
        echo "  --embeddings-only  Only generate embeddings"
        echo "  --validation-only  Only run validation"
        echo "  --start-only       Only start the application"
        echo
        echo "Environment variables:"
        echo "  OPENAI_API_KEY     OpenAI API key (required)"
        echo "  GEMINI_API_KEY     Google Gemini API key (required)"
        echo
        exit 0
        ;;
    --embeddings-only)
        source venv/bin/activate 2>/dev/null || { print_error "Virtual environment not found. Run full setup first."; exit 1; }
        generate_embeddings
        generate_analytics
        exit 0
        ;;
    --validation-only)
        source venv/bin/activate 2>/dev/null || { print_error "Virtual environment not found. Run full setup first."; exit 1; }
        run_validation
        test_openai
        exit 0
        ;;
    --start-only)
        source venv/bin/activate 2>/dev/null || { print_error "Virtual environment not found. Run full setup first."; exit 1; }
        start_app
        exit 0
        ;;
    "")
        # No arguments, run full setup
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run the main setup
main