![image](https://github.com/user-attachments/assets/c6066ec1-a2d8-4d66-b925-6405558d08e3)

# Simple Docker Agent

A lightweight Python-based agent that provides real-time monitoring of Docker containers and host system resources.

## Features

- **REST API**: Exposes a `/status` endpoint for easy integration.
- **Container Insights**: Reports CPU, memory (raw and humanized), uptime, ports, labels, and more for each container.
- **Host Metrics**: Shows CPU, memory, and disk usage for the host (raw and humanized).
- **Fast & Lightweight**: Designed for quick responses, even with many containers.
- **Easy Deployment**: Runs as a Docker container with minimal configuration.

---

## Quick Start

## Run from Docker Hub (method 1)

You can run the latest public version of **Simple Docker Agent** directly from Docker Hub, with no need to build the image yourself.

```bash
docker pull solutionforest/simple-docker-agent:latest

docker run -d \
  --name simple-docker-agent \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --privileged \
  solutionforest/simple-docker-agent:latest
```

- The agent will now be accessible at [http://localhost:8080/status](http://localhost:8080/status).
- Make sure to mount the Docker socket (`-v /var/run/docker.sock:/var/run/docker.sock`) to allow the agent to access container information.
- The `--privileged` flag may be required for collecting some host metrics.

You can also specify a version instead of `latest`, for example:

```bash
docker pull solutionforest/simple-docker-agent:1.0.0
docker run -d \
  --name simple-docker-agent \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --privileged \
  solutionforest/simple-docker-agent:1.0.0
```

**See [solutionforest/simple-docker-agent on Docker Hub](https://hub.docker.com/r/solutionforest/simple-docker-agent) for available tags and more info.**


### 1. Build the Agent Docker Image (method 2)

```bash
git clone https://github.com/solutionforest/simple-docker-agent
cd simple-docker-agent
docker build -t simple-docker-agent .
```

### 2. Run the Agent

```bash
docker run -d \
  --name docker-agent \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --privileged \
  simple-docker-agent
```

### 3. Query the Status API

```bash
curl http://localhost:8080/status | jq
```

---

## Example Response

```json
{
  "host": {
    "cpu_percent": 4.5,
    "memory": {
      "total": 16777216000,
      "used": 2548039680,
      "percent": 15.2,
      "total_human": "16.8 GB",
      "used_human": "2.5 GB"
    },
    "disk": {
      "total": 128849018880,
      "used": 64424509440,
      "percent": 50.0,
      "total_human": "128.8 GB",
      "used_human": "64.4 GB"
    }
  },
  "docker_services": [
    {
      "id": "abcdef123456...",
      "name": "my-service",
      "status": "running",
      "image": ["nginx:latest"],
      "stats": {
        "cpu_percent": 0.21,
        "cpu_human": "0.21%",
        "mem_usage_bytes": 25600000,
        "mem_usage_human": "25.6 MB",
        "mem_limit_bytes": 2147483648,
        "mem_limit_human": "2.1 GB"
      },
      "created_at": "2024-05-01T12:00:00Z",
      "started_at": "2024-05-01T12:01:00Z",
      "uptime_seconds": 3600,
      "uptime_human": "1 hour",
      "restart_count": 0,
      "ports": {
        "80/tcp": [
          {
            "HostIp": "0.0.0.0",
            "HostPort": "8081"
          }
        ]
      },
      "labels": {
        "com.docker.compose.project": "myproject"
      }
    }
    // ...more containers
  ]
}
```

---

## Configuration

- **Port**: Default is `8080` (see `agent.py`).
- **Docker socket**: Mount `/var/run/docker.sock` for API access.
- **Privileges**: The container may require `--privileged` for resource stats.

---

## Security

**Do not expose the agent’s API to the public internet without authentication or firewall protection.**  
For production deployments, consider running behind a reverse proxy and securing the endpoint.

---

## License

MIT License

---

## Credits

- [psutil](https://github.com/giampaolo/psutil)
- [docker-py](https://github.com/docker/docker-py)
- [humanize](https://github.com/jmoiron/humanize)
- [Flask](https://github.com/pallets/flask)

---

## Contributing

Pull requests and feature suggestions are welcome!
