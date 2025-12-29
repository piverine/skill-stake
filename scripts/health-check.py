#!/usr/bin/env python3
"""
Health check script for Skill-Stake Learning Platform
Verifies that all services are running and accessible
"""

import requests
import sys
import time

def check_service(name, url, timeout=30):
    """Check if a service is responding"""
    print(f"Checking {name} at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is healthy")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(2)
    
    print(f"❌ {name} is not responding")
    return False

def main():
    """Run health checks for all services"""
    services = [
        ("Backend API", "http://localhost:8000/health"),
        ("Frontend", "http://localhost:3000"),
        ("Backend API Docs", "http://localhost:8000/docs"),
    ]
    
    print("🏥 Running health checks for Skill-Stake Learning Platform...")
    print("=" * 60)
    
    all_healthy = True
    for name, url in services:
        if not check_service(name, url):
            all_healthy = False
    
    print("=" * 60)
    if all_healthy:
        print("🎉 All services are healthy!")
        sys.exit(0)
    else:
        print("⚠️  Some services are not responding")
        sys.exit(1)

if __name__ == "__main__":
    main()