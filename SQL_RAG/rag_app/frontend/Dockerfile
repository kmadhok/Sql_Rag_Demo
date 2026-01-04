# React Frontend Dockerfile for SQL RAG Application
# Multi-stage build: Node.js for building, Nginx for serving
# Optimized for Google Cloud Run deployment

# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies for Vite build)
RUN npm ci

# Copy source code
COPY . ./

# Build argument for API URL (injected at build time for Vite compilation)
# NO DEFAULT - must be explicitly provided via --build-arg
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# === PRODUCTION HARDENING: Validate build arg ===
# Fail immediately if VITE_API_BASE_URL is empty
# This prevents silently building with localhost fallback
RUN if [ -z "$VITE_API_BASE_URL" ]; then \
      echo "========================================" && \
      echo "ERROR: VITE_API_BASE_URL is empty!" && \
      echo "========================================" && \
      echo "" && \
      echo "Build must provide:" && \
      echo "  --build-arg VITE_API_BASE_URL=<backend-url>" && \
      echo "" && \
      echo "Example:" && \
      echo "  docker build --build-arg VITE_API_BASE_URL=https://api.example.com ." && \
      echo "" && \
      exit 1; \
    fi

# Debug output to verify correct URL is being used
RUN echo "========================================" && \
    echo "Build Configuration:" && \
    echo "  VITE_API_BASE_URL = $VITE_API_BASE_URL" && \
    echo "========================================" && \
    echo ""

# Build the React application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built React app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
