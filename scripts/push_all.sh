#!/bin/bash
# Synchronizes both repositories (finanzplan and Open-finanz-overview)
echo "Pushing to origin (finanzplan)..."
git push origin main
echo "Pushing to Open-finanz-overview..."
if git remote | grep -q "^open-repo$"; then
    git push open-repo main
elif git remote | grep -q "^overview$"; then
    git push overview main
fi
echo "Done! Both repositories are synchronized."
