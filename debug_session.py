#!/usr/bin/env python3
"""
Utility module to help debug session problems.
"""
from fastapi import Request

def print_session_debug(request: Request):
    """Print debug information about the request session."""
    print("\n=== SESSION DEBUG INFO ===")
    print(f"Request URL: {request.url}")
    print(f"Session in scope: {'session' in request.scope}")
    
    if 'session' in request.scope:
        print("Session contents:")
        try:
            for key, value in request.session.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error accessing session items: {e}")
    else:
        print("No session found in request scope")
    
    print("Headers:")
    for name, value in request.headers.items():
        if name.lower() in ('cookie', 'set-cookie'):
            print(f"  {name}: [REDACTED]")  # Don't print actual cookie values
        else:
            print(f"  {name}: {value}")
    
    print("=========================\n")
