#!/usr/bin/env python3
"""
Check .env file for duplicate entries and email configuration issues
"""

import os
from pathlib import Path

def check_env_file():
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return
    
    print("📁 Found .env file, checking contents...")
    
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Track variables and their values
    variables = {}
    duplicates = {}
    empty_values = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
            
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Check for duplicates
            if key in variables:
                if key not in duplicates:
                    duplicates[key] = [variables[key]]
                duplicates[key].append((i, value))
            else:
                variables[key] = (i, value)
            
            # Check for empty values
            if not value:
                empty_values.append((i, key))
    
    # Report findings
    print(f"\n📊 Found {len(variables)} unique variables")
    
    # Email-related variables
    email_vars = ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD']
    print("\n📧 EMAIL CONFIGURATION:")
    for var in email_vars:
        if var in variables:
            line_num, value = variables[var]
            if var == 'EMAIL_HOST_PASSWORD' and value:
                value = '*' * len(value)
            print(f"  ✅ {var} = {value} (line {line_num})")
        else:
            print(f"  ❌ {var} = NOT SET")
    
    # Report duplicates
    if duplicates:
        print(f"\n⚠️  DUPLICATE VARIABLES FOUND:")
        for key, occurrences in duplicates.items():
            print(f"  🔄 {key}:")
            for line_num, value in occurrences:
                display_value = value if key != 'EMAIL_HOST_PASSWORD' else ('*' * len(value) if value else 'EMPTY')
                print(f"    Line {line_num}: {display_value}")
    else:
        print("\n✅ No duplicate variables found")
    
    # Report empty values
    if empty_values:
        print(f"\n⚠️  EMPTY VALUES FOUND:")
        for line_num, key in empty_values:
            print(f"  Line {line_num}: {key} = (empty)")
    else:
        print("\n✅ No empty values found")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if duplicates:
        print("  - Remove duplicate variable definitions")
        print("  - Keep only the last (most recent) definition")
    if empty_values:
        print("  - Remove or populate empty variables")
    if not any(var in variables for var in email_vars):
        print("  - Add missing email configuration variables")
    
    print("\n🔧 To fix duplicates, edit .env file and remove earlier duplicate lines")

if __name__ == "__main__":
    check_env_file() 