FROM node:22-alpine
WORKDIR /app
COPY server.mjs .
RUN apk upgrade --no-cache && rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
USER node
EXPOSE 7861
CMD ["node", "server.mjs"]
