# docker build --no-cache -t ai-agent:latest -f Dockerfile .

# --- Стадия сборки (Builder) ---
FROM python:3.13-slim AS builder

WORKDIR /bot

# Устанавливаем git, если необходимо скачать зависимости из репозиториев
#RUN #apt-get update && \
#    apt-get install -y --no-install-recommends git && \
#    rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvloop

# Копируем исходный код бота
COPY . .

# --- Стадия финального образа (Production) ---
#FROM python:3.11-slim AS production

#WORKDIR /bot

# Если некоторые пакеты требуют системных библиотек на runtime,
# установите их здесь (пример: libssl-dev для cryptography и т.п.)
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends <нужные пакеты> && \
#     rm -rf /var/lib/apt/lists/*

# Копируем все установленные python-зависимости из builder-образа
#COPY --from=builder /usr/local/lib/python3.11/site-packages \
#                    /usr/local/lib/python3.11/site-packages

# Копируем проект
#COPY --from=builder /bot /bot

# Запускаем бота
CMD ["python", "/bot/agent.py"]
