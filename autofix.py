"""
Automatic Fix Script for Rayeva AI Complete
Fixes SQLAlchemy 2.0 compatibility issues

Usage: python auto_fix.py
"""

import re
import os

print("🔧 Rayeva AI - Automatic Fix Script")
print("=" * 50)

# Check if original file exists
if not os.path.exists('rayeva_ai_complete.py'):
    print("❌ Error: rayeva_ai_complete.py not found!")
    print("Make sure this script is in the same folder as rayeva_ai_complete.py")
    exit(1)

print("✅ Found rayeva_ai_complete.py")
print("📖 Reading file...")

with open('rayeva_ai_complete.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Applying fixes...")

# Fix 1: Update import for DeclarativeBase
print("  - Fixing import statement...")
content = content.replace(
    'from sqlalchemy.ext.declarative import declarative_base',
    'from sqlalchemy.orm import DeclarativeBase'
)

# Fix 2: Remove ARRAY from import (not needed)
content = content.replace(
    'from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, JSON, Enum as SQLEnum, ARRAY, func',
    'from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, JSON, Enum as SQLEnum, func, text'
)

# Fix 3: Update Base class declaration
print("  - Fixing Base class...")
content = content.replace(
    'Base = declarative_base()',
    'class Base(DeclarativeBase):\n    pass'
)

# Fix 4: Rename metadata column to ai_metadata
print("  - Renaming metadata column...")
content = content.replace(
    'metadata = Column(JSON, nullable=True)  # Store as JSON',
    'ai_metadata = Column(JSON, nullable=True)  # Renamed from metadata'
)

# Fix 5: Update parameter names in method signatures
print("  - Updating parameter names...")
content = re.sub(
    r'metadata: Optional\[Dict\[str, Any\]\] = None\) -> Dict\[str, Any\]:',
    r'request_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:',
    content
)

# Fix 6: Update parameter usage
content = content.replace('"metadata": metadata or {}', '"request_metadata": request_metadata or {}')
content = content.replace('metadata=metadata', 'request_metadata=request_metadata')
content = content.replace('metadata={"', 'request_metadata={"')

# Fix 7: Update _log_interaction signature
content = re.sub(
    r'metadata: Optional\[Dict\[str, Any\]\] = None\s*\):',
    r'ai_metadata: Optional[Dict[str, Any]] = None):',
    content
)

# Fix 8: Update _log_interaction body
content = content.replace(
    'metadata=metadata or {}',
    'ai_metadata=ai_metadata or {}'
)

# Fix 9: Fix health check
print("  - Fixing health check...")
content = content.replace(
    'db.execute("SELECT 1")',
    'db.execute(text("SELECT 1"))'
)

print("💾 Writing fixed file...")

# Write fixed file
with open('rayeva_ai_complete_FIXED.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed file created: rayeva_ai_complete_FIXED.py")
print()
print("🎉 All done! Now run:")
print("   python rayeva_ai_complete_FIXED.py")
print()
print("Or rename the fixed file:")
print("   Windows: move rayeva_ai_complete_FIXED.py rayeva_ai_complete.py")
print("   Linux/Mac: mv rayeva_ai_complete_FIXED.py rayeva_ai_complete.py")