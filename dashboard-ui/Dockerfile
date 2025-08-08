# Multi-stage build for React + Vite application

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better Docker layer caching
COPY package*.json ./

# Install all dependencies (including dev dependencies for building)
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage  
FROM node:20-alpine AS production

# Create non-root user first, before copying files
RUN addgroup -g 1001 -S nodejs && \
    adduser -S dashboard -u 1001 -G nodejs

# Create app directory with correct ownership
RUN mkdir -p /app && chown -R dashboard:nodejs /app

WORKDIR /app

# Switch to non-root user
USER dashboard

# Copy package files with correct ownership
COPY --chown=dashboard:nodejs package*.json ./

# Install only production dependencies
RUN npm install --omit=dev && npm cache clean --force

# Copy built application from builder stage with correct ownership
COPY --from=builder --chown=dashboard:nodejs /app/dist ./dist

# Copy server file with correct ownership
COPY --chown=dashboard:nodejs server.js ./

# Expose port 3000
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Start the Express server
CMD ["node", "server.js"]