#!/bin/bash
set -e

POD_NAME="roots-graph"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Load .env (handles values with spaces)
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

NEO4J_PASSWORD="${NEO4J_PASSWORD:-changeme}"
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
OPENROUTER_MODEL="${OPENROUTER_MODEL:-anthropic/claude-sonnet-4}"

usage() {
  echo "Usage: $0 {start|stop|restart|status|logs|build}"
  echo ""
  echo "  start    - Create pod and start all services"
  echo "  stop     - Stop and remove the pod"
  echo "  restart  - Stop then start"
  echo "  status   - Show pod and container status"
  echo "  logs     - Tail logs from all containers"
  echo "  build    - Build backend and frontend images"
  exit 1
}

build_images() {
  echo "Building backend image..."
  podman build -t roots-graph-backend "$SCRIPT_DIR/backend"

  echo "Building frontend image..."
  podman build -t roots-graph-frontend "$SCRIPT_DIR/frontend"

  echo "Images built."
}

start_pod() {
  # Check if pod exists
  if podman pod exists "$POD_NAME" 2>/dev/null; then
    echo "Pod already exists. Use '$0 restart' to recreate."
    podman pod start "$POD_NAME"
    return
  fi

  echo "Creating pod: $POD_NAME"
  podman pod create --name "$POD_NAME" \
    -p 3000:3000 \
    -p 8000:8000 \
    -p 7474:7474 \
    -p 7687:7687

  echo "Starting Neo4j..."
  podman run -d --pod "$POD_NAME" \
    --name "${POD_NAME}-neo4j" \
    -e "NEO4J_AUTH=neo4j/$NEO4J_PASSWORD" \
    -e 'NEO4J_PLUGINS=["apoc"]' \
    -e NEO4J_server_memory_heap_initial__size=256m \
    -e NEO4J_server_memory_heap_max__size=512m \
    -v neo4j-data:/data \
    -v neo4j-logs:/logs \
    docker.io/library/neo4j:5

  # Wait for Neo4j to be ready
  echo "Waiting for Neo4j..."
  for i in $(seq 1 30); do
    if podman exec "${POD_NAME}-neo4j" neo4j status 2>/dev/null | grep -q "running"; then
      break
    fi
    sleep 2
  done
  echo "Neo4j ready."

  echo "Starting backend..."
  podman run -d --pod "$POD_NAME" \
    --name "${POD_NAME}-backend" \
    -e "NEO4J_URI=bolt://127.0.0.1:7687" \
    -e "NEO4J_USER=neo4j" \
    -e "NEO4J_PASSWORD=$NEO4J_PASSWORD" \
    -e "FRONTEND_URL=http://localhost:3000" \
    -e "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" \
    -e "OPENROUTER_MODEL=$OPENROUTER_MODEL" \
    roots-graph-backend

  echo "Starting frontend..."
  podman run -d --pod "$POD_NAME" \
    --name "${POD_NAME}-frontend" \
    -e "NEXT_PUBLIC_API_URL=http://localhost:8000" \
    roots-graph-frontend

  echo ""
  echo "Roots Graph is running!"
  echo "  Frontend:  http://localhost:3000"
  echo "  API:       http://localhost:8000/docs"
  echo "  Neo4j:     http://localhost:7474"
  echo ""
}

stop_pod() {
  if podman pod exists "$POD_NAME" 2>/dev/null; then
    echo "Stopping pod: $POD_NAME"
    podman pod stop "$POD_NAME" 2>/dev/null || true
    podman pod rm "$POD_NAME" -f 2>/dev/null || true
    echo "Pod stopped and removed."
  else
    echo "Pod not running."
  fi
}

show_status() {
  if podman pod exists "$POD_NAME" 2>/dev/null; then
    podman pod ps --filter "name=$POD_NAME"
    echo ""
    podman ps --filter "pod=$POD_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  else
    echo "Pod not running."
  fi
}

show_logs() {
  local container="${2:-all}"
  if [ "$container" = "all" ]; then
    podman pod logs -f "$POD_NAME"
  else
    podman logs -f "${POD_NAME}-${container}"
  fi
}

case "${1:-}" in
  start)
    start_pod
    ;;
  stop)
    stop_pod
    ;;
  restart)
    stop_pod
    start_pod
    ;;
  status)
    show_status
    ;;
  logs)
    show_logs "$@"
    ;;
  build)
    build_images
    ;;
  *)
    usage
    ;;
esac
