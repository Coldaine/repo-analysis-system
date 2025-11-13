#!/bin/bash

# Agentic Repository Analysis System - Prototype Runner
# This script executes the agentic prototype and handles setup/teardown

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    local packages=("requests" "pyyaml")
    for package in "${packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            warning "Python package '$package' not found. Installing..."
            pip3 install "$package"
        fi
    done
    
    # Check configuration file
    if [[ ! -f "config.yaml" ]]; then
        error "Configuration file config.yaml not found"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p review_logging/visualizations
    mkdir -p review_logging/rendered
    mkdir -p review_logging/summaries
    
    success "Prerequisites check completed"
}

# Set up environment variables
setup_environment() {
    log "Setting up environment variables..."
    
    # Export mock API keys for prototype (in production, these would be real)
    export GITHUB_TOKEN="${GITHUB_TOKEN:-mock_github_token_for_prototype}"
    export GLM_API_KEY="${GLM_API_KEY:-mock_glm_api_key_for_prototype}"
    export MINIMAX_API_KEY="${MINIMAX_API_KEY:-mock_minimax_api_key_for_prototype}"
    export GOOGLE_SEARCH_KEY="${GOOGLE_SEARCH_KEY:-mock_google_search_key_for_prototype}"
    
    # Set Python path
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    
    success "Environment variables set up"
}

# Run the prototype
run_prototype() {
    log "Starting Agentic Repository Analysis System Prototype..."
    
    # Run the Python script
    if python3 agentic_prototype.py; then
        success "Prototype execution completed successfully"
        
        # Display results
        display_results
        
        return 0
    else
        error "Prototype execution failed"
        return 1
    fi
}

# Display execution results
display_results() {
    log "Displaying execution results..."
    
    # Find the latest report
    local latest_report=$(find logs -name "prototype-run-*.md" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [[ -n "$latest_report" ]]; then
        echo
        success "Latest analysis report: $latest_report"
        echo
        echo "Report preview:"
        echo "================"
        head -20 "$latest_report"
        echo "================"
        echo
        echo "Full report available at: $(pwd)/$latest_report"
    else
        warning "No analysis report found"
    fi
    
    # Display generated visualizations
    local viz_files=(review_logging/visualizations/*.mmd)
    if [[ -f "${viz_files[0]}" ]]; then
        echo
        success "Generated visualizations:"
        for viz_file in "${viz_files[@]}"; do
            if [[ -f "$viz_file" ]]; then
                echo "  - $(basename "$viz_file")"
            fi
        done
    fi
    
    # Display log file
    if [[ -f "logs/prototype.log" ]]; then
        echo
        success "Execution log: logs/prototype.log"
        echo "Recent log entries:"
        echo "=================="
        tail -10 logs/prototype.log
        echo "=================="
    fi
}

# Optional: Render Mermaid diagrams (if mmdc is available)
render_visualizations() {
    log "Attempting to render Mermaid diagrams..."
    
    if command -v mmdc &> /dev/null; then
        local viz_files=(review_logging/visualizations/*.mmd)
        local rendered_dir="review_logging/rendered"
        
        for viz_file in "${viz_files[@]}"; do
            if [[ -f "$viz_file" ]]; then
                local basename=$(basename "$viz_file" .mmd)
                local output_file="$rendered_dir/${basename}.svg"
                
                log "Rendering $(basename "$viz_file") to SVG..."
                mmdc -i "$viz_file" -o "$output_file" -t neutral -w 1200 -H 800
                
                if [[ -f "$output_file" ]]; then
                    success "Rendered: $output_file"
                fi
            fi
        done
    else
        warning "Mermaid CLI (mmdc) not found. Skipping diagram rendering"
        warning "To install: npm install -g @mermaid-js/mermaid-cli"
    fi
}

# Clean up old files
cleanup() {
    log "Cleaning up old files..."
    
    # Remove reports older than 7 days
    find logs -name "prototype-run-*.md" -type f -mtime +7 -delete 2>/dev/null || true
    
    # Remove old log files
    find logs -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    
    success "Cleanup completed"
}

# Show usage information
show_usage() {
    echo "Agentic Repository Analysis System - Prototype Runner"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -c, --clean    Clean up old files before running"
    echo "  -r, --render   Attempt to render Mermaid diagrams"
    echo "  -v, --verbose  Enable verbose output"
    echo
    echo "Examples:"
    echo "  $0                    # Run prototype with default settings"
    echo "  $0 --clean --render   # Clean old files and render diagrams"
    echo "  $0 --verbose          # Run with verbose output"
}

# Main execution
main() {
    local clean_before_run=false
    local render_diagrams=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--clean)
                clean_before_run=true
                shift
                ;;
            -r|--render)
                render_diagrams=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                set -x  # Enable command tracing
                shift
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Display header
    echo "========================================"
    echo "Agentic Repository Analysis System"
    echo "Prototype Runner"
    echo "========================================"
    echo
    
    # Clean up if requested
    if [[ "$clean_before_run" == true ]]; then
        cleanup
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Set up environment
    setup_environment
    
    # Run the prototype
    if run_prototype; then
        # Render visualizations if requested
        if [[ "$render_diagrams" == true ]]; then
            render_visualizations
        fi
        
        echo
        success "Prototype execution completed successfully!"
        echo
        echo "Next steps:"
        echo "1. Review the analysis report in the logs/ directory"
        echo "2. Examine generated visualizations in review_logging/visualizations/"
        echo "3. Check execution logs in logs/prototype.log"
        
        if [[ "$render_diagrams" == false ]]; then
            echo "4. Run with --render flag to generate SVG diagrams"
        fi
        
    else
        error "Prototype execution failed!"
        echo
        echo "Troubleshooting:"
        echo "1. Check logs/prototype.log for detailed error information"
        echo "2. Verify config.yaml is properly configured"
        echo "3. Ensure all required Python packages are installed"
        echo "4. Run with --verbose flag for detailed output"
        
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"