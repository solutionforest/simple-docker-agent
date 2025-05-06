import psutil
import docker
import humanize
import concurrent.futures
from flask import Flask, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

def get_host_resources():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_percent = psutil.cpu_percent(interval=0)  # non-blocking, instantaneous
    return {
        'cpu_percent': cpu_percent,
        'memory': {
            'total': mem.total,
            'used': mem.used,
            'percent': mem.percent,
            'total_human': humanize.naturalsize(mem.total),
            'used_human': humanize.naturalsize(mem.used)
        },
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'percent': disk.percent,
            'total_human': humanize.naturalsize(disk.total),
            'used_human': humanize.naturalsize(disk.used)
        }
    }

def calculate_cpu_percent(stat):
    try:
        cpu_delta = stat["cpu_stats"]["cpu_usage"]["total_usage"] - stat["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stat["cpu_stats"]["system_cpu_usage"] - stat["precpu_stats"]["system_cpu_usage"]
        num_cpus = len(stat["cpu_stats"]["cpu_usage"].get("percpu_usage", [])) or 1
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
            return round(cpu_percent, 2)
    except Exception:
        pass
    return None

def fetch_container_info(c):
    stats = {}
    cpu_percent = None
    mem_usage = None
    mem_usage_human = None
    mem_limit = None
    mem_limit_human = None
    created_at = None
    started_at = None
    uptime_seconds = None
    uptime_human = None
    restart_count = None
    ports = None
    labels = None

    # Get resource stats
    try:
        stats = c.stats(stream=False)
        cpu_percent = calculate_cpu_percent(stats)
        mem_usage = stats.get('memory_stats', {}).get('usage', None)
        mem_limit = stats.get('memory_stats', {}).get('limit', None)
        mem_usage_human = humanize.naturalsize(mem_usage) if mem_usage is not None else None
        mem_limit_human = humanize.naturalsize(mem_limit) if mem_limit is not None else None
    except Exception:
        pass

    # Get timestamps and uptime
    try:
        created_at = c.attrs['Created']
        started_at = c.attrs['State']['StartedAt']
        # Calculate uptime
        start_ts = datetime.fromisoformat(started_at.replace('Z', '+00:00')).timestamp()
        now_ts = datetime.now(timezone.utc).timestamp()
        uptime_seconds = int(now_ts - start_ts)
        uptime_human = humanize.precisedelta(uptime_seconds)
    except Exception:
        pass

    # Get restart count
    try:
        restart_count = c.attrs['RestartCount'] if 'RestartCount' in c.attrs else c.attrs['State']['RestartCount']
    except Exception:
        restart_count = None

    # Get ports
    try:
        ports = c.attrs['NetworkSettings']['Ports']
    except Exception:
        ports = None

    # Get labels
    try:
        labels = c.labels
    except Exception:
        labels = None

    service_info = {
        'id': c.id,
        'name': c.name,
        'status': c.status,
        'image': c.image.tags,
        'stats': {
            'cpu_percent': cpu_percent,
            'cpu_human': f"{cpu_percent}%" if cpu_percent is not None else "N/A",
            'mem_usage_bytes': mem_usage,
            'mem_usage_human': mem_usage_human,
            'mem_limit_bytes': mem_limit,
            'mem_limit_human': mem_limit_human
        },
        'created_at': created_at,
        'started_at': started_at,
        'uptime_seconds': uptime_seconds,
        'uptime_human': uptime_human,
        'restart_count': restart_count,
        'ports': ports,
        'labels': labels
    }
    return service_info

def get_docker_services():
    client = docker.from_env()
    containers = client.containers.list(all=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        services = list(executor.map(fetch_container_info, containers))
    return services

@app.route('/status')
def status():
    return jsonify({
        'host': get_host_resources(),
        'docker_services': get_docker_services()
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)