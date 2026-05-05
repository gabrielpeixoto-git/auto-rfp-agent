FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Build the application
RUN npm run build

# Create .next directory and set permissions
RUN mkdir -p .next && chmod -R 777 .next

EXPOSE 3000

# Use host 0.0.0.0 to accept connections from outside container
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# Start in production mode (uses standalone output from next.config.js)
CMD ["npm", "start"]
