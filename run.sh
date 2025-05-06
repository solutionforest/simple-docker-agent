# Run the agent (needs Docker socket access)
docker run -d \
  --name docker-agent \
  -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --privileged \
  simple-docker-agent