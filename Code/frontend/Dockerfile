# Use a Node.js base image
FROM node:18-alpine

# Set the working directory
WORKDIR /app/frontend

RUN apk update && apk add --no-cache curl

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Expose the port the React dev server will run on
EXPOSE 3000

# Command to start the React development server
CMD ["npm", "start"]