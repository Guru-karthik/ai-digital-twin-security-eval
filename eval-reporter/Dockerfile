FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY reporter ./reporter
RUN useradd --system --uid 10001 reporter
USER reporter
EXPOSE 9200
# results are mounted read-only at /results
CMD ["python", "-m", "reporter", "serve", "--results", "/results"]
