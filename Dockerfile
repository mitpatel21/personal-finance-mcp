FROM python:3.11-slim
LABEL io.modelcontextprotocol.server.name="io.github.JosueM1109/personal-finance-mcp"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py plaid_client.py auth.py ./
# Inside a container the server must listen on all interfaces; publish the
# port as 127.0.0.1:8000:8000 on the host to keep it local.
ENV HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "server.py"]
