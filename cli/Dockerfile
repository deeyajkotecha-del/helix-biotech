FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy built files
COPY dist ./dist

# Create cache directory
RUN mkdir -p cache

# Expose port (Railway will override with PORT env var)
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3001}/api/health || exit 1

# Start the server
CMD ["node", "dist/cli.js", "serve"]
