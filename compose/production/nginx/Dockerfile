# Stage 0, "build-stage", based on Node.js, to build and compile the frontend

FROM node:10 as build-stage

WORKDIR /app

COPY package*.json /app/

RUN npm install

COPY ./ /app/

RUN npm run build

RUN mv /app/node_modules/ol/ol.css /app/router-map/static/css/ol.css

RUN mv /app/node_modules/bootstrap/dist/css/bootstrap.min.css /app/router-map/static/css/bootstrap.min.css

RUN mv /app/node_modules/bootstrap/dist/css/bootstrap.min.css.map /app/router-map/static/css/bootstrap.min.css.map




# Stage 1, based on Nginx, to have only the compiled app, ready for production with Nginx

FROM nginx:1.15

COPY --from=build-stage /app/router-map/static /usr/share/nginx/html/static
