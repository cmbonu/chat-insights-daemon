docker build --tag gcr.io/chatanalysis-270612/chat-insights-daemon:v2 .
docker run --publish 8100:5000 --detach --name chatidv2 gcr.io/chatanalysis-270612/chat-insights-daemon:v2
docker push gcr.io/chatanalysis-270612/chat-insights-daemon:v2