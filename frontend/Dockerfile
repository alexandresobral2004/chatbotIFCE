FROM node:20-alpine

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json* ./
# O postinstall (patch-package) precisa dos patches ja na instalacao
RUN npm install

# Copy source code
COPY . .

# Accept build arguments and expose them as env variables for Next.js build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application
RUN npm run build

# Expose port 3000
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })" || exit 1

CMD ["npm", "start"]