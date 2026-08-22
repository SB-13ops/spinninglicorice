# syntax=docker/dockerfile:1
# WaxStack web image (Next.js, standalone output).
#
# Build context is apps/web/ — on Railway set this service's Root Directory to
# apps/web. Two stages: a builder that compiles the app, and a slim runner that
# serves the traced standalone output with `node server.js`.

# ---- Builder ----------------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app

# IMPORTANT: NEXT_PUBLIC_* variables are inlined into the client bundle at BUILD
# time, not read at runtime. So the API base URL must be provided as a build arg
# and promoted to an env var before `next build`. On Railway, set
# NEXT_PUBLIC_API_BASE_URL as a service variable — Railway passes it to the build.
ARG NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000/api/v1"
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

# Install dependencies from the lockfile for a reproducible build.
COPY package.json package-lock.json ./
RUN npm ci

# Build the app. next.config.mjs sets output:"standalone".
COPY . .
RUN npm run build

# ---- Runner -----------------------------------------------------------------
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# Next's standalone server reads PORT and HOSTNAME. Bind all interfaces so
# Railway's proxy can reach it; default PORT for local `docker run`.
ENV HOSTNAME=0.0.0.0 \
    PORT=3000

# Run as a non-root user.
RUN addgroup -g 10001 nodejs && adduser -u 10001 -G nodejs -S nextjs

# Copy only what the standalone server needs: the traced server + node_modules,
# the static assets, and the public dir (if present).
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# public/ is optional; the trailing "./" copy is a no-op if it doesn't exist.
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
