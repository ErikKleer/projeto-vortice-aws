import json
import boto3
import time
from datetime import datetime, timedelta

# --- Configurações ---
INSTANCE_ID = 'i-xxxxxxxxxxxxxxxxx'
REGION = 'sa-east-1'
SCHEDULER_ROLE_ARN = "ARN_DA_SUA_IAM_ROLE_AQUI"
GRACE_PERIOD_MINUTES = 5
SCHEDULE_NAME = 'VorticeFinalCheckSchedule'
# --------------------

ec2 = boto3.client('ec2', region_name=REGION)
ssm = boto3.client('ssm', region_name=REGION)
scheduler = boto3.client('scheduler', region_name=REGION)

def get_rcon_password():
    try:
        parameter = ssm.get_parameter(Name='SecureString', WithDecryption=True)
        return parameter['Parameter']['Value']
    except Exception as e:
        print(f"Erro ao buscar a senha no Parameter Store: {str(e)}")
        raise e

RCON_PASSWORD = get_rcon_password()

def get_player_count():
    print("Enviando comando via SSM para obter a contagem de jogadores...")
    command = f'mcrcon -H 127.0.0.1 -P 25575 -p "{RCON_PASSWORD}" "list"'
    try:
        response = ssm.send_command(
            InstanceIds=[INSTANCE_ID],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
            TimeoutSeconds=30
        )
        command_id = response['Command']['CommandId']
        time.sleep(2.5)
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=INSTANCE_ID)

        if output['Status'] != 'Success':
             print(f"Comando SSM falhou ou excedeu o tempo limite. Status: {output['Status']}")
             print(f"Saída de erro: {output.get('StandardErrorContent', 'N/A')}")
             return -1

        command_output = output['StandardOutputContent']
        if "Connection refused" in command_output:
            print("Erro de RCON: Conexão recusada.")
            return -1

        parts = command_output.split(' ')
        if len(parts) > 2 and parts[0] == "There" and parts[1] == "are" and parts[2].isdigit():
             player_count = int(parts[2])
             print(f"Contagem de jogadores em tempo real: {player_count}")
             return player_count
        else:
            print(f"Não foi possível extrair a contagem de jogadores da resposta: '{command_output}'")
            return -1
    except Exception as e:
        print(f"Erro ao executar o comando SSM: {str(e)}")
        return -1

def shutdown_sequence():
    try:
        print(f"Enviando comando para parar a instância {INSTANCE_ID}...")
        ec2.stop_instances(InstanceIds=[INSTANCE_ID])
        return "Comando de desligamento enviado com sucesso."
    except Exception as e:
        print(f"Erro durante o desligamento: {str(e)}")
        return f"Erro durante o desligamento: {str(e)}"

def create_shutdown_schedule(lambda_context):
    print(f"Servidor vazio. Criando agendamento para verificação final em {GRACE_PERIOD_MINUTES} minutos.")
    lambda_arn = lambda_context.invoked_function_arn
    try:
        schedule_time = (datetime.utcnow() + timedelta(minutes=GRACE_PERIOD_MINUTES)).isoformat(timespec='seconds')
        schedule_time_str = (datetime.utcnow() + timedelta(minutes=GRACE_PERIOD_MINUTES)).strftime('%Y-%m-%dT%H:%M:%S')

        scheduler.create_schedule(
            Name=SCHEDULE_NAME,
            ActionAfterCompletion='DELETE',
            ScheduleExpression=f'at({schedule_time_str})',
            Target={
                'Arn': lambda_arn,
                'RoleArn': SCHEDULER_ROLE_ARN,
                'Input': '{"source": "self-scheduled-check"}'
            },
            FlexibleTimeWindow={'Mode': 'OFF'}
        )
        return f"Verificação final agendada para {schedule_time_str} UTC."
    except scheduler.exceptions.ConflictException:
        print("Agendamento conflitante encontrado. Tentando remover o antigo...")
        try:
            scheduler.delete_schedule(Name=SCHEDULE_NAME)
            print("Agendamento antigo removido. Tente o evento novamente.")
            return "Um agendamento antigo foi encontrado e removido. Por favor, acione o evento novamente."
        except Exception as delete_e:
            print(f"Erro ao tentar remover agendamento conflitante: {str(delete_e)}")
            return f"Erro ao tentar remover agendamento conflitante: {str(delete_e)}"
    except Exception as e:
        print(f"!!! ERRO AO CRIAR AGENDAMENTO: {str(e)}")
        return f"Erro ao criar agendamento: {str(e)}"


def lambda_handler(event, context):
    try:
        instance_response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        if not instance_response['Reservations'] or not instance_response['Reservations'][0]['Instances']:
            print("Instância não encontrada.")
            return {'statusCode': 404, 'body': json.dumps("Instance not found")}
        instance_state = instance_response['Reservations'][0]['Instances'][0]['State']['Name']

        if instance_state != 'running':
            message = f"Verificação cancelada. A instância não está 'running' (estado: {instance_state})."
            print(message)
            return {'statusCode': 200, 'body': json.dumps(message)}
    except Exception as desc_e:
         print(f"Erro ao descrever instância: {str(desc_e)}")
         return {'statusCode': 500, 'body': json.dumps(f"Error checking instance status: {str(desc_e)}")}


    if event.get('source') == 'self-scheduled-check':
        print("Executando verificação final agendada.")
        player_count = get_player_count()
        if player_count == 0:
            print("Confirmado: Servidor ainda vazio. Iniciando desligamento.")
            message = shutdown_sequence()
        elif player_count > 0 :
            message = f"Desligamento cancelado. {player_count} jogador(es) entraram no servidor."
            print(message)
        else:
             message = "Não foi possível determinar a contagem de jogadores na verificação final. Desligamento cancelado por segurança."
             print(message)

    else:
        print("Log (jogador saiu). Verificando se foi o último...")
        player_count = get_player_count()
        if player_count == 0:
            message = create_shutdown_schedule(context)
        elif player_count > 0:
            message = f"{player_count} jogadores ainda conectados. Nenhuma ação tomada."
            print(message)
        else:
            message = "Não foi possível determinar a contagem de jogadores após evento de log. Nenhuma ação tomada por segurança."
            print(message)

    final_status_code = 500 if "Erro" in message and "agendamento" not in message else 200
    return {'statusCode': final_status_code, 'body': json.dumps(message)}
