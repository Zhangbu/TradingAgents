#!/usr/bin/env python3
"""
Quick Start Script for TradingAgents API
Run this to start the API server with default configuration.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ['fastapi', 'uvicorn', 'sqlalchemy', 'apscheduler']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Run: pip install " + " ".join(missing))
        return False
    
    return True


def check_environment():
    """Check environment variables."""
    env_vars = ['OPENAI_API_KEY']
    missing = []
    
    for var in env_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing)}")
        print("Some features may not work without these.")
    
    return True


def main():
    """Main entry point."""
    print("=" * 50)
    print("🚀 TradingAgents API Server")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Initialize database
    print("\n📦 Initializing database...")
    from api.database import init_db
    init_db()
    print("✅ Database initialized")
    
    # Start server
    print("\n🌐 Starting API server...")
    print("📍 API: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    # Run server
    from api.main import run_server
    run_server()


if __name__ == "__main__":
    main()