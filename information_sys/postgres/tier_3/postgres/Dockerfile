FROM bitnamilegacy/postgresql-repmgr:17.6.0-debian-12-r2

# The upstream image runs as UID 1001 but creates its passwd entry only in the
# entrypoint process through libnss_wrapper. A permanent entry also makes
# administrative commands started with `docker compose exec` resolve the user.
USER 0
RUN if ! getent passwd 1001 >/dev/null; then \
      printf 'postgres:x:1001:0:PostgreSQL:/bitnami/postgresql:/bin/false\n' >> /etc/passwd; \
    fi
USER 1001
