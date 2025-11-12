FROM node:18-alpine

WORKDIR /app

# Copy package files from the frontend directory
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Note: Source code mounted via volume for hot-reload
# COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
