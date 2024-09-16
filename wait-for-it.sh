#!/bin/bash

host_port="$1"
shift
cmd="$@"

host=$(echo "$host_port" | cut -d':' -f1)
port=$(echo "$host_port" | cut -d':' -f2)

until nc -z "$host" "$port"; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"
exec $cmd
