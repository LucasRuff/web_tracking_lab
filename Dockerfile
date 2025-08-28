FROM python:3.11-slim

WORKDIR /app
COPY index.html beacon_server.py start_servers.sh /app/

# Expose both ports
EXPOSE 8081

# Run the shell script as entrypoint
CMD ["./start_servers.sh"]
RUN chmod +x /app/start_servers.sh