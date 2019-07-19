FROM redis:5.0.5-alpine

RUN echo vm.overcommit_memory=1 > /etc/sysctl.conf
CMD redis-server --requirepass "${REDIS_PASSWORD}"
