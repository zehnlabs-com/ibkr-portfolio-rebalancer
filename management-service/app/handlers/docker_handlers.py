"""
Docker container management handlers
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import HTTPException
import docker
from docker.errors import DockerException, APIError, NotFound


class DockerHandlers:
    """Handlers for Docker container management"""
    
    def __init__(self):
        self.docker_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Docker client with error handling"""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            print("Docker client connected successfully")
        except DockerException as e:
            print(f"Warning: Failed to connect to Docker: {str(e)}")
            print("Docker functionality will be disabled")
            self.docker_client = None
    
    async def get_containers(self) -> List[Dict]:
        """Get list of all containers with status"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            if not self.docker_client:
                raise HTTPException(status_code=503, detail="Docker connection not available")
                
            # Get all containers (running and stopped)
            containers = self.docker_client.containers.list(all=True)
            
            container_list = []
            for container in containers:
                # Get container stats if running
                stats = None
                if container.status == 'running':
                    try:
                        # Get one-shot stats (non-streaming)
                        stats_data = container.stats(stream=False)
                        stats = self._parse_container_stats(stats_data)
                    except Exception as e:
                        # Continue if stats fail - just log it
                        print(f"Failed to get stats for {container.name}: {e}")
                
                # Safely get image name
                image_name = 'unknown'
                try:
                    if container.image and hasattr(container.image, 'tags') and container.image.tags:
                        image_name = container.image.tags[0]
                    elif container.image and hasattr(container.image, 'id'):
                        # Use image ID if no tags available
                        image_name = container.image.id[:12]
                except Exception as e:
                    # If image info fails, try to get from attrs
                    image_name = container.attrs.get('Config', {}).get('Image', 'unknown')
                
                container_info = {
                    'id': container.id[:12],  # Short ID
                    'name': container.name,
                    'image': image_name,
                    'status': container.status,
                    'state': container.attrs.get('State', {}).get('Status', 'unknown'),
                    'created': container.attrs.get('Created', ''),
                    'ports': self._format_ports(container.ports),
                    'labels': container.labels,
                    'stats': stats,
                    'last_update': datetime.now().isoformat()
                }
                container_list.append(container_info)
            
            return container_list
            
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get containers: {str(e)}")
    
    async def get_container_stats(self, container_name: str) -> Dict:
        """Get detailed stats for a specific container"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            container = self.docker_client.containers.get(container_name)
            
            if container.status != 'running':
                raise HTTPException(status_code=400, detail=f"Container {container_name} is not running")
            
            # Get current stats
            stats_data = container.stats(stream=False)
            parsed_stats = self._parse_container_stats(stats_data)
            
            return {
                'container_name': container_name,
                'status': container.status,
                'stats': parsed_stats,
                'last_update': datetime.now().isoformat()
            }
            
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get container stats: {str(e)}")
    
    async def get_container_logs(self, container_name: str, tail: int = 100) -> List[str]:
        """Get logs from a specific container"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            container = self.docker_client.containers.get(container_name)
            
            # Get logs with tail limit
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            log_lines = logs.split('\n') if logs else []
            
            # Filter out empty lines
            log_lines = [line.strip() for line in log_lines if line.strip()]
            
            return log_lines
            
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}")
    
    async def start_container(self, container_name: str) -> Dict:
        """Start a container"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            # Check if container is critical
            if self._is_critical_service(container_name):
                raise HTTPException(status_code=403, detail=f"Cannot start critical service {container_name} via API")
                
            container = self.docker_client.containers.get(container_name)
            
            if container.status == 'running':
                return {
                    'message': f"Container {container_name} is already running",
                    'status': 'running'
                }
            
            container.start()
            
            # Wait a moment for status to update
            await asyncio.sleep(1)
            container.reload()
            
            return {
                'message': f"Container {container_name} started successfully",
                'status': container.status
            }
            
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")
    
    async def stop_container(self, container_name: str) -> Dict:
        """Stop a container"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            # Check if container is critical
            if self._is_critical_service(container_name):
                raise HTTPException(status_code=403, detail=f"Cannot stop critical service {container_name} via API")
                
            container = self.docker_client.containers.get(container_name)
            
            if container.status != 'running':
                return {
                    'message': f"Container {container_name} is not running",
                    'status': container.status
                }
            
            container.stop(timeout=10)  # 10 second graceful shutdown
            
            # Wait for status to update
            await asyncio.sleep(2)
            container.reload()
            
            return {
                'message': f"Container {container_name} stopped successfully",
                'status': container.status
            }
            
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop container: {str(e)}")
    
    async def restart_container(self, container_name: str) -> Dict:
        """Restart a container"""
        try:
            if not self.docker_client:
                self._initialize_client()
                
            # Check if container is critical
            if self._is_critical_service(container_name):
                raise HTTPException(status_code=403, detail=f"Cannot restart critical service {container_name} via API")
                
            container = self.docker_client.containers.get(container_name)
            container.restart(timeout=10)
            
            # Wait for restart to complete
            await asyncio.sleep(3)
            container.reload()
            
            return {
                'message': f"Container {container_name} restarted successfully",
                'status': container.status
            }
            
        except NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except DockerException as e:
            raise HTTPException(status_code=500, detail=f"Docker error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to restart container: {str(e)}")
    
    def _parse_container_stats(self, stats_data: Dict) -> Dict:
        """Parse Docker stats into useful metrics"""
        try:
            # CPU usage calculation
            cpu_delta = stats_data['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats_data['precpu_stats']['cpu_usage']['total_usage']
            system_cpu_delta = stats_data['cpu_stats']['system_cpu_usage'] - \
                              stats_data['precpu_stats']['system_cpu_usage']
            
            cpu_usage_percent = 0.0
            if system_cpu_delta > 0 and cpu_delta > 0:
                number_cpus = stats_data['cpu_stats']['online_cpus']
                cpu_usage_percent = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
            
            # Memory usage
            memory_usage = stats_data['memory_stats'].get('usage', 0)
            memory_limit = stats_data['memory_stats'].get('limit', 0)
            memory_usage_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0
            
            # Network I/O
            networks = stats_data.get('networks', {})
            network_rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
            network_tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
            
            # Block I/O
            blkio_stats = stats_data.get('blkio_stats', {})
            io_service_bytes_recursive = blkio_stats.get('io_service_bytes_recursive', [])
            
            block_read = sum(item.get('value', 0) for item in io_service_bytes_recursive if item.get('op') == 'Read')
            block_write = sum(item.get('value', 0) for item in io_service_bytes_recursive if item.get('op') == 'Write')
            
            return {
                'cpu_usage_percent': round(cpu_usage_percent, 2),
                'memory_usage_bytes': memory_usage,
                'memory_limit_bytes': memory_limit,
                'memory_usage_percent': round(memory_usage_percent, 2),
                'network_rx_bytes': network_rx_bytes,
                'network_tx_bytes': network_tx_bytes,
                'block_read_bytes': block_read,
                'block_write_bytes': block_write,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # Return basic stats if parsing fails
            return {
                'error': f"Failed to parse stats: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _format_ports(self, ports: Dict) -> List[str]:
        """Format container port mappings for display"""
        port_list = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get('HostPort')
                    if host_port:
                        port_list.append(f"{host_port}:{container_port}")
        return port_list
    
    def _is_critical_service(self, container_name: str) -> bool:
        """Check if a container is a critical service that shouldn't be controlled via API"""
        critical_services = [
            'management-service',  # This service itself
            'redis',              # Data store
            'ibkr-gateway'        # Trading connection
        ]
        return container_name in critical_services