# Опыты с отказами etcd-варианта

Повторите четыре опыта из `tier_4/docs/02-failures.md`: отказ standby, отказ
текущего PostgreSQL leader, межсерверный partition и потеря всего удалённого
сервера. Дополнительно перед и после каждого опыта фиксируйте quorum:

```bash
docker compose -f compose.remote.yml exec etcd-1 \
  etcdctl endpoint status --cluster -w table
```

Ожидание: сторона с quorum DCS может владеть лидерским lock; сторона без quorum
не получает новый lock и не создаёт второй primary.
