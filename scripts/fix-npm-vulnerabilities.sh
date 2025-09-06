#!/bin/bash

# Fix npm security vulnerabilities in web frontend

echo "🔒 Fixing npm security vulnerabilities..."

cd web

# First, try automatic fix
echo "📦 Running npm audit fix..."
npm audit fix

# If there are still issues, try force fix (with caution)
if npm audit | grep -q "vulnerabilities"; then
    echo "⚠️  Some vulnerabilities remain. Attempting force fix..."
    echo "Note: This may introduce breaking changes."
    read -p "Continue with force fix? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm audit fix --force
    fi
fi

# Update to latest compatible versions
echo "📈 Updating to latest compatible versions..."
npm update

# Final audit report
echo "📋 Final security audit:"
npm audit

echo "✅ Vulnerability fixes completed!"
