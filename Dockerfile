FROM python:3.12-alpine

WORKDIR /app
COPY index.html beacon_server.py /app/

# Expose both ports
ENV PORT=8080
EXPOSE 8080

# Run the shell script as entrypoint
CMD ["python", "beacon_server.py"]