
"""
System Health Router
Provides real-time server statistics (CPU, RAM, Disk, Net, GPU, Process).
"""
import psutil
import time
import os
import subprocess
import xml.etree.ElementTree as ET
from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()

# Global state for calculating network speed
last_net_io = psutil.net_io_counters()
last_net_time = time.time()

def get_cpu_info() -> Dict[str, Any]:
    """Get CPU usage, frequency, and temperature."""
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq() # current, min, max
    
    # Try to get temperature (Linux only)
    temp = 0.0
    try:
        temps = psutil.sensors_temperatures()
        # Common keys for CPU temp: 'coretemp', 'k10temp', 'cpu_thermal'
        for key in ['coretemp', 'k10temp', 'cpu_thermal']:
            if key in temps:
                temp = temps[key][0].current
                break
    except:
        pass

    return {
        "usage": cpu_percent,
        "frequency": cpu_freq.current if cpu_freq else 0,
        "temperature": temp,
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True)
    }

def get_memory_info() -> Dict[str, Any]:
    """Get RAM and Swap usage."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "ram": {
            "total": mem.total,
            "used": mem.used,
            "percent": mem.percent,
            "free": mem.available
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "percent": swap.percent
        }
    }

def get_disk_info() -> Dict[str, Any]:
    """Get Disk usage and IO."""
    # Usage of root partition
    usage = psutil.disk_usage('/')
    io = psutil.disk_io_counters()
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": usage.percent,
        "read_bytes": io.read_bytes if io else 0,
        "write_bytes": io.write_bytes if io else 0
    }

def get_network_info() -> Dict[str, Any]:
    """Get current Network Speed (Upload/Download)."""
    global last_net_io, last_net_time
    
    current_net_io = psutil.net_io_counters()
    current_time = time.time()
    
    # Avoid div by zero
    time_delta = current_time - last_net_time
    if time_delta < 0.1: 
        time_delta = 0.1
        
    bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
    bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
    
    # Update state
    last_net_io = current_net_io
    last_net_time = current_time
    
    return {
        "upload_speed": bytes_sent / time_delta,   # Bytes/sec
        "download_speed": bytes_recv / time_delta  # Bytes/sec
    }

def get_gpu_info() -> List[Dict[str, Any]]:
    """Get GPU info via nvidia-smi (if available)."""
    gpus = []
    try:
        # Run nvidia-smi -x -q for XML output
        result = subprocess.run(['nvidia-smi', '-x', '-q'], capture_output=True, text=True)
        if result.returncode == 0:
            root = ET.fromstring(result.stdout)
            for gpu in root.findall('gpu'):
                name = gpu.find('product_name').text
                util = gpu.find('utilization/gpu_util').text.replace('%', '').strip()
                mem_used = gpu.find('fb_memory_usage/used').text.replace('MiB', '').strip()
                mem_total = gpu.find('fb_memory_usage/total').text.replace('MiB', '').strip()
                temp = gpu.find('temperature/gpu_temp').text.replace('C', '').strip()
                
                gpus.append({
                    "name": name,
                    "usage": int(util),
                    "memory_used": int(mem_used),
                    "memory_total": int(mem_total),
                    "temperature": int(temp)
                })
    except Exception:
        pass # GPU not found or error
    return gpus

def get_bot_status() -> Dict[str, Any]:
    """Get stats for the Bot process."""
    bot_stats = {
        "status": "offline",
        "cpu_percent": 0,
        "memory_percent": 0,
        "memory_usage": 0,
        "threads": 0,
        "uptime": 0
    }
    
    # Try to find python process running main.py
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python' in proc.info['name'] and any('main.py' in arg for arg in cmdline):
                # Found it
                # cpu_percent needs a blocking call or interval, which psutil handles internally on subsequent calls
                # For first call it might be 0, but that's fine for polling.
                
                mem = proc.info['memory_info']
                bot_stats = {
                    "status": "online",
                    "pid": proc.info['pid'],
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_usage": mem.rss, # Resident Set Size
                    "threads": proc.num_threads(),
                    "uptime": time.time() - proc.info['create_time']
                }
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    return bot_stats

@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Data aggregation for Dashboard."""
    return {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "gpu": get_gpu_info(),
        "bot": get_bot_status(),
        "timestamp": time.time()
    }
