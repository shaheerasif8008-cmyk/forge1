# Multi-stage Dockerfile for Next.js SSR deployment with standalone output
# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_ENV_LABEL=Production
ARG NEXT_PUBLIC_GIT_SHA=unknown

# Set build-time environment variables
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_ENV_LABEL=$NEXT_PUBLIC_ENV_LABEL
ENV NEXT_PUBLIC_GIT_SHA=$NEXT_PUBLIC_GIT_SHA
ENV NEXT_TELEMETRY_DISABLED=1

# Build the Next.js application with standalone output
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy standalone build
# The standalone folder contains the minimal node_modules and server files
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Set runtime environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Use dynamic port binding (Azure Container Apps sets PORT)
ENV PORT=3000
EXPOSE 3000

# Switch to non-root user
USER nextjs

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application using the standalone server
CMD ["node", "server.js"]