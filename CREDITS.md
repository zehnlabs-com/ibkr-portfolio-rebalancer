# Credits & Acknowledgments

This project is built on the shoulders of many excellent open source projects. We'd like to acknowledge and thank the maintainers and contributors of these projects.

## Docker Images

### [Redis](https://redis.io/) - `redis:7-alpine`
**License**: BSD 3-Clause  
**Usage**: Primary message queue and caching layer for event processing  
**Repository**: https://github.com/redis/redis

### [gnzsnz/ib-gateway](https://hub.docker.com/r/gnzsnz/ib-gateway) 
**License**: Apache 2.0  
**Usage**: Containerized Interactive Brokers Gateway with VNC access  
**Repository**: https://github.com/gnzsnz/ib-gateway  
**Maintainer**: Guillermo Navas-Palencia (@gnzsnz)

### [NoVNC](https://novnc.com/) - `dougw/novnc`
**License**: MPL-2.0  
**Usage**: Web-based VNC client for remote IBKR Gateway access  
**Repository**: https://github.com/novnc/noVNC  
**Docker Image**: https://hub.docker.com/r/dougw/novnc

## Python Libraries

### Core Dependencies

**[ib-insync](https://github.com/erdewit/ib_insync)** - Interactive Brokers API  
**License**: BSD 2-Clause  
**Usage**: Python wrapper for Interactive Brokers TWS API  
**Maintainer**: Ewald de Wit (@erdewit)

**[FastAPI](https://fastapi.tiangolo.com/)** - Web Framework  
**License**: MIT  
**Usage**: Management Service REST API  
**Repository**: https://github.com/tiangolo/fastapi  
**Maintainer**: Sebastián Ramirez (@tiangolo)

**[Redis-py](https://github.com/redis/redis-py)** - Redis Client  
**License**: MIT  
**Usage**: Python client for Redis queue operations  
**Repository**: https://github.com/redis/redis-py

**[Ably](https://ably.com/)** - Real-time Messaging  
**License**: Apache 2.0  
**Usage**: Event ingestion from Zehnlabs real-time streams  
**Repository**: https://github.com/ably/ably-python  
**SDK**: Python SDK for Ably real-time messaging platform

### Utility Libraries

**[Pydantic](https://pydantic.dev/)** - Data Validation  
**License**: MIT  
**Usage**: Data models and validation across services  
**Repository**: https://github.com/pydantic/pydantic

**[Loguru](https://github.com/Delgan/loguru)** - Logging  
**License**: MIT  
**Usage**: Structured JSON logging across all services  
**Maintainer**: Antoine Catel (@Delgan)

**[PyYAML](https://pyyaml.org/)** - YAML Processing  
**License**: MIT  
**Usage**: Configuration file parsing  
**Repository**: https://github.com/yaml/pyyaml

**[python-dotenv](https://github.com/theskumar/python-dotenv)** - Environment Variables  
**License**: BSD 3-Clause  
**Usage**: Loading environment variables from .env files  
**Maintainer**: Saurabh Kumar (@theskumar)

**[Uvicorn](https://www.uvicorn.org/)** - ASGI Server  
**License**: BSD 3-Clause  
**Usage**: High-performance server for Management Service API  
**Repository**: https://github.com/encode/uvicorn

**[aiohttp](https://docs.aiohttp.org/)** - Async HTTP Client  
**License**: Apache 2.0  
**Usage**: HTTP requests to allocation APIs  
**Repository**: https://github.com/aio-libs/aiohttp

**[nest-asyncio](https://github.com/erdewit/nest_asyncio)** - Async Support  
**License**: BSD 2-Clause  
**Usage**: Nested asyncio event loop support  
**Maintainer**: Ewald de Wit (@erdewit)  

## Development Tools

**[Docker](https://www.docker.com/)** - Containerization  
**License**: Apache 2.0  
**Usage**: Container orchestration and deployment

**[Docker Compose](https://docs.docker.com/compose/)** - Multi-container Applications  
**License**: Apache 2.0  
**Usage**: Service orchestration and development environment

## Special Thanks

- **Interactive Brokers** for providing the TWS API that makes automated trading possible
- The entire **open source community** for building and maintaining these incredible tools

---

*If you notice we've missed crediting any project or if you'd like to update information about your project, please open an issue or submit a pull request.*