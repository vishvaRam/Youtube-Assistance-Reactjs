# Use a Node.js base image for building the React app
FROM node:18-alpine as builder

# Set the working directory
WORKDIR /app/frontend

RUN apk update && apk add --no-cache curl

# Copy package.json and package-lock.json (if you have one)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Build the React app for production
RUN npm run build

# Use a lightweight Nginx image to serve the static files
FROM nginx:alpine

# Remove default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy the built React app from the builder stage into Nginx's public directory
COPY --from=builder /app/frontend/build /usr/share/nginx/html

# Copy a custom Nginx configuration to handle React routing (optional but recommended)
# This will prevent 404 errors on direct access to React routes
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose the port Nginx will serve on
EXPOSE 80

# Command to start Nginx
CMD ["nginx", "-g", "daemon off;"]