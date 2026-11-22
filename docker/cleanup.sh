# Docker Build optimization and maintenance script

#!/bin/bash

set -e

echo "🧹 Docker Cleanup Script"
echo "======================="
echo ""

# Remove unused images
echo "Removing dangling images..."
docker image prune -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Remove build cache
read -p "Remove build cache? This will force full rebuilds (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker builder prune -f
fi

echo ""
echo "✅ Cleanup complete!"
echo ""

# Show disk usage
echo "📊 Docker disk usage:"
docker system df
