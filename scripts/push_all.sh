#!/bin/bash
# Synchronizes both repositories (finanzplan and Open-finanz-overview)
echo "Pushing to origin (finanzplan)..."
git push origin main
echo "Pushing to overview (Open-finanz-overview)..."
git push overview main
echo "Done! Both repositories are synchronized."
