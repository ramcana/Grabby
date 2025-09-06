#!/bin/bash

# Grabby Testing Script
# Comprehensive testing of all components and interfaces

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Grabby Comprehensive Testing Suite${NC}"
echo "=" * 50

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run scripts/install.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Function to run test and capture result
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}🔄 Running: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        return 1
    fi
}

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0

# 1. Python Import Tests
echo -e "\n${BLUE}📦 Testing Python Imports${NC}"

test_imports() {
    python -c "
import sys
sys.path.insert(0, '.')

try:
    from backend.core.downloader import UniversalDownloader
    from backend.core.unified_downloader import create_downloader
    from backend.core.queue_manager import QueueManager
    from backend.core.event_bus import EventBus
    from backend.core.rules_engine import RulesEngine
    from backend.api.fastapi_app import app
    from config.profile_manager import ProfileManager
    print('✅ All core imports successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    exit(1)
"
}

run_test "Core Module Imports" "test_imports"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# 2. CLI Interface Tests
echo -e "\n${BLUE}💻 Testing CLI Interface${NC}"

run_test "CLI Help Command" "python -m cli.main --help > /dev/null"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

run_test "CLI Profiles Command" "python -m cli.profiles list > /dev/null"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# 3. API Tests
echo -e "\n${BLUE}🌐 Testing API Endpoints${NC}"

# Start API server in background for testing
echo "Starting API server for testing..."
uvicorn backend.api.fastapi_app:app --host 127.0.0.1 --port 8001 > /dev/null 2>&1 &
API_PID=$!
sleep 3

# Test API endpoints
test_api_health() {
    curl -s -f http://127.0.0.1:8001/health > /dev/null
}

test_api_stats() {
    curl -s -f http://127.0.0.1:8001/stats > /dev/null
}

test_api_profiles() {
    curl -s -f http://127.0.0.1:8001/profiles > /dev/null
}

run_test "API Health Check" "test_api_health"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

run_test "API Stats Endpoint" "test_api_stats"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

run_test "API Profiles Endpoint" "test_api_profiles"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# Stop API server
kill $API_PID 2>/dev/null || true

# 4. Component Integration Tests
echo -e "\n${BLUE}🔧 Testing Component Integration${NC}"

run_test "Integration Tests" "python tests/test_integration.py"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# 5. Performance Benchmarks
echo -e "\n${BLUE}⚡ Running Performance Benchmarks${NC}"

run_test "Performance Benchmarks" "python tests/test_performance.py"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# 6. Configuration Tests
echo -e "\n${BLUE}⚙️  Testing Configuration${NC}"

test_config() {
    python -c "
from config.profile_manager import ProfileManager
pm = ProfileManager()
profiles = pm.list_profiles()
assert 'default' in profiles
assert 'audio_only' in profiles
print('✅ Profile configuration valid')
"
}

run_test "Profile Configuration" "test_config"
((TOTAL_TESTS++))
[ $? -eq 0 ] && ((PASSED_TESTS++))

# 7. Docker Tests (if Docker is available)
if command -v docker &> /dev/null; then
    echo -e "\n${BLUE}🐳 Testing Docker Configuration${NC}"
    
    test_docker_build() {
        docker build -f Dockerfile.api -t grabby-test . > /dev/null 2>&1
    }
    
    run_test "Docker API Build" "test_docker_build"
    ((TOTAL_TESTS++))
    [ $? -eq 0 ] && ((PASSED_TESTS++))
    
    # Clean up test image
    docker rmi grabby-test > /dev/null 2>&1 || true
fi

# 8. Web Frontend Tests (if Node.js is available)
if command -v npm &> /dev/null && [ -d "web" ]; then
    echo -e "\n${BLUE}🌐 Testing Web Frontend${NC}"
    
    test_web_install() {
        cd web && npm install > /dev/null 2>&1 && cd ..
    }
    
    test_web_build() {
        cd web && npm run build > /dev/null 2>&1 && cd ..
    }
    
    run_test "Web Dependencies Install" "test_web_install"
    ((TOTAL_TESTS++))
    [ $? -eq 0 ] && ((PASSED_TESTS++))
    
    run_test "Web Frontend Build" "test_web_build"
    ((TOTAL_TESTS++))
    [ $? -eq 0 ] && ((PASSED_TESTS++))
fi

# Test Summary
echo ""
echo "=" * 50
echo -e "${BLUE}📊 Test Results Summary${NC}"
echo "=" * 50

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}🎉 All tests passed! ($PASSED_TESTS/$TOTAL_TESTS)${NC}"
    echo -e "${GREEN}✅ Grabby is ready for deployment!${NC}"
    exit_code=0
else
    echo -e "${YELLOW}⚠️  Some tests failed: $PASSED_TESTS/$TOTAL_TESTS passed${NC}"
    echo -e "${YELLOW}📝 Check the output above for details${NC}"
    exit_code=1
fi

echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Start services: ./scripts/start.sh"
echo "2. Access web UI: http://localhost:3000"
echo "3. Check API docs: http://localhost:8000/docs"
echo "4. Try CLI: python -m cli.main --help"
echo "5. Launch TUI: python -m cli.tui_app"

exit $exit_code
