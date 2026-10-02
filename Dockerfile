FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
RUN python -m pip install --no-cache-dir .
CMD ["sh", "-c", "modelagree run examples/demo.yaml && modelagree score runs/demo > /dev/null && modelagree report runs/demo"]
