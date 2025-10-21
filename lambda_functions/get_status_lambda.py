import json
import boto3

# --- Variáveis de Configuração ---
REGION = 'sa-east-1'
INSTANCE_ID = 'i-xxxxxxxxxxxxxxxxx'
# ------------------------------------

ec2 = boto3.client('ec2', region_name=REGION)

def lambda_handler(event, context):
    response_payload = {}
    status_code = 200

    try:
        response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        if not response['Reservations'] or not response['Reservations'][0]['Instances']:
            raise ValueError(f"Instance {INSTANCE_ID} not found.")
        instance = response['Reservations'][0]['Instances'][0]
        instance_state = instance['State']['Name']
        response_payload['status'] = instance_state

        if instance_state == 'running':
            public_ip = instance.get('PublicIpAddress', 'IP não encontrado')
            response_payload['ip'] = public_ip
    except Exception as e:
        print(f"Ocorreu um erro: {str(e)}")
        response_payload = {'status': 'error', 'message': str(e)}
        status_code = 500

    return {
        'statusCode': status_code,
        'headers': { 'Access-Control-Allow-Origin': '*' },
        'body': json.dumps(response_payload)
    }
