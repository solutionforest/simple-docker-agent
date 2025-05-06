import psutil
import docker
import humanize
import concurrent.futures
from flask import Flask, jsonify, send_from_directory
from datetime import datetime, timezone
import os

app = Flask(__name__)

def get_host_resources():
    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(datetime.now(timezone.utc).timestamp() - boot_time)
    # Load average
    load1, load5, load15 = psutil.getloadavg()
    # CPU
    cpu_times = psutil.cpu_times_percent(interval=0)
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=0)
    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    # Disk
    disk = psutil.disk_usage('/')
    # IO
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters(pernic=True)
    # Processes
    procs = list(psutil.process_iter(['status']))
    running = sum(1 for p in procs if p.info['status'] == psutil.STATUS_RUNNING)
    blocked = sum(1 for p in procs if p.info['status'] == psutil.STATUS_DISK_SLEEP)
    # Interrupts (if available)
    interrupts = None
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("intr"):
                    interrupts = int(line.split()[1])
    except Exception:
        interrupts = None

    return {
        "uptime_seconds": uptime_seconds,
        "uptime_human": humanize.precisedelta(uptime_seconds),
        "boot_time": datetime.fromtimestamp(boot_time, tz=timezone.utc).isoformat(),
        "cpu": {
            "percent": cpu_percent,
            "idle_percent": cpu_times.idle,
            "count": cpu_count,
            "times": cpu_times._asdict()
        },
        "memory": {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "buffers": getattr(mem, "buffers", 0),
            "cached": getattr(mem, "cached", 0),
            "total_human": humanize.naturalsize(mem.total),
            "used_human": humanize.naturalsize(mem.used),
            "available_human": humanize.naturalsize(mem.available),
            "buffers_human": humanize.naturalsize(getattr(mem, "buffers", 0)),
            "cached_human": humanize.naturalsize(getattr(mem, "cached", 0)),
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
            "sin": swap.sin,
            "sout": swap.sout,
            "total_human": humanize.naturalsize(swap.total),
            "used_human": humanize.naturalsize(swap.used),
            "free_human": humanize.naturalsize(swap.free),
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "total_human": humanize.naturalsize(disk.total),
            "used_human": humanize.naturalsize(disk.used),
            "free_human": humanize.naturalsize(disk.free)
        },
        "disk_io": {
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_time": getattr(disk_io, 'read_time', None),
            "write_time": getattr(disk_io, 'write_time', None)
        },
        "net_io": {
            dev: {
                "bytes_sent": val.bytes_sent,
                "bytes_recv": val.bytes_recv,
                "packets_sent": val.packets_sent,
                "packets_recv": val.packets_recv,
                "errin": val.errin,
                "errout": val.errout,
                "dropin": val.dropin,
                "dropout": val.dropout
            }
            for dev, val in net_io.items()
        },
        "loadavg": {
            "1min": load1,
            "5min": load5,
            "15min": load15
        },
        "processes": {
            "running": running,
            "blocked_io": blocked
        },
        "interrupts": interrupts
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

@app.route('/dashboard.html')
def dashboard():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
