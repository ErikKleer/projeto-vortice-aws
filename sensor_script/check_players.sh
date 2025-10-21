#!/bin/bash

# --- Configurações ---
RCON_HOST="127.0.0.1"
RCON_PORT="25575"
REGION="sa-east-1"
# --------------------

RCON_PASSWORD=$(aws ssm get-parameter --name "SecureString" --with-decryption --query "Parameter.Value" --output text --region $REGION)

if [ -z "$RCON_PASSWORD" ]; then
    echo "Erro crítico: Não foi possível obter a senha RCON do Parameter Store."
    exit 1
fi

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
PLAYER_COUNT=$(mcrcon -H $RCON_HOST -P $RCON_PORT -p "$RCON_PASSWORD" "list" | awk '{print $3}')

if ! [[ "$PLAYER_COUNT" =~ ^[0-9]+$ ]]; then
    echo "Erro ao obter a contagem de jogadores. O servidor pode estar offline."
    PLAYER_COUNT=0
fi

echo "Jogadores online: $PLAYER_COUNT"

aws cloudwatch put-metric-data \
    --metric-name PlayerCount \
    --namespace "VorticeProject" \
    --value $PLAYER_COUNT \
    --dimensions InstanceId=$INSTANCE_ID \
    --region $REGION

echo "Métrica enviada para o CloudWatch com sucesso."
