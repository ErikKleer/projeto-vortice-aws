import json
import boto3

# --- Variáveis de Configuração ---
REGION = 'sa-east-1'
INSTANCE_ID = 'i-xxxxxxxxxxxxxxxxx'
# ------------------------------------

ec2 = boto3.client('ec2', region_name=REGION)

def lambda_handler(event, context):
    print("Recebida requisição para iniciar o servidor Vórtice.")

    try:
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        message = "Comando de inicialização recebido. O servidor está sendo ligado. Verificando o status..."
        status_code = 200
    except Exception as e:
        print(f"Ocorreu um erro: {str(e)}")
        message = f"Erro ao enviar comando de inicialização: {str(e)}"
        status_code = 500

    return {
        'statusCode': status_code,
        'headers': { 'Access-Control-Allow-Origin': '*' },
        'body': json.dumps({'message': message})
    }
