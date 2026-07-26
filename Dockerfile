FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY src/ ./src/
COPY pyproject.toml ./
RUN pip install --no-cache-dir --user -e . && \
    chown -R nobody:nogroup /app
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import sys, urllib.request; \
    sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status == 200 else 1)"
CMD ["python", "-m", "src.main"]