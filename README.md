# RUPN Server

Публичный Docker-контейнер для запуска своего RUPN сервера.

Архитектура: один контейнер = один серверный инстанс. Здесь нет приватного backend, SQLite, Telegram bot, reconciler, пула нод и мультисессий. При старте контейнер генерирует или переиспользует одну пару `room/key`, запускает ровно один `olcrtc -mode srv` и печатает JWT-ссылку для подключения.

Flow: `ENV → [Validate config] → (missing/invalid env) → [Generate or load room/key] → (olcrtc gen error) → [Start one server process] → (runtime error) → [Print JWT link] → Ready`

## Быстрый запуск

```bash
docker run --rm -it \
  --name rupn-server \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest
```

В логах будет:

```text
RUPN server started
RUPN_CONNECT_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
RUPN_CONNECT_URI=olcrtc://...
```

Для приложения используй `RUPN_CONNECT_JWT`.

## Запуск через Docker Compose

```bash
mkdir ruvpn-server
cd ruvpn-server
curl -O https://raw.githubusercontent.com/makamekm/ruvpn-server/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/makamekm/ruvpn-server/main/.env.example
docker compose up -d
docker logs -f rupn-server
```

## Env переменные

- `RUPN_CARRIER`: carrier для комнаты. По умолчанию `wbstream`.
- `RUPN_TRANSPORT`: транспорт. По умолчанию `datachannel`.
- `RUPN_LINK`: тип линка. По умолчанию `direct`.
- `RUPN_DNS`: DNS upstream. По умолчанию `1.1.1.1:53`.
- `RUPN_CLIENT_ID`: client id, который попадёт в ссылку. По умолчанию `android-01`.
- `RUPN_JWT_SECRET`: секрет подписи JWT. По умолчанию `rupn` для совместимости с Android-клиентом.
- `RUPN_DEBUG`: `true/false`, включает debug logs olcrtc.
- `RUPN_ROTATE_ON_START`: `true/false`. По умолчанию `false`, поэтому ссылка сохраняется в volume и переживает restart.
- `RUPN_SOCKS_PROXY` + `RUPN_SOCKS_PROXY_PORT`: опциональный SOCKS5 proxy для egress сервера.

## Обновить ссылку

Если нужно выпустить новую ссылку:

```bash
docker run --rm -it \
  -e RUPN_ROTATE_ON_START=true \
  -v rupn-server-state:/var/lib/rupn-server \
  makame/rupn-server:latest
```

Или удалить volume:

```bash
docker compose down -v
docker compose up -d
```

## Сборка локально

```bash
git clone https://github.com/makamekm/ruvpn-server.git
cd ruvpn-server
docker build -t makame/rupn-server:latest .
docker run --rm -it -v rupn-server-state:/var/lib/rupn-server makame/rupn-server:latest
```

## Безопасность

- Не публикуй `RUPN_CONNECT_URI`: там лежит сырой ключ.
- Для пользователя отдавай `RUPN_CONNECT_JWT`.
- Если меняешь `RUPN_JWT_SECRET`, Android-клиент должен знать тот же секрет, иначе JWT не пройдёт проверку.
- Volume `/var/lib/rupn-server` содержит `server.json` с ключом, держи его приватным.
