# Projeto Vórtice: Servidor de Minecraft On-Demand com Automação Serverless na AWS

## 📄 Resumo
O Projeto Vórtice implementa uma plataforma inteligente e de custo otimizado para hospedar um servidor de Minecraft privado na AWS. **Este projeto foi desenvolvido como um estudo prático dos serviços fundamentais da AWS, visando aprofundar o conhecimento na plataforma e servir como preparação para a certificação AWS Certified Cloud Practitioner.** Ele opera "on-demand", utilizando uma arquitetura serverless para iniciar automaticamente o servidor através de uma interface web quando necessário e desligá-lo durante períodos de inatividade, reduzindo efetivamente os custos ociosos a zero.

---

## 🖥️ Painel de Controle
A interface web simples permite iniciar o servidor e visualizar seu status atual, incluindo o endereço IP para conexão.

**[IMAGEM: Screenshot do index.html]**

---

## 🎯 O Problema
Servidores de jogos privados, quando hospedados 24/7 na nuvem, geram custos significativos mesmo quando não há jogadores online. Além disso, o processo de iniciar e parar o servidor manualmente é ineficiente, requer acesso técnico e não oferece uma experiência amigável para uma comunidade de jogadores.

---

## 💡 A Solução
Foi construído um sistema automatizado e orientado a eventos na AWS, composto por:
1.  **Painel de Controle Web:** Um site estático que permite iniciar o servidor com um clique e monitorar seu status.
2.  **Motor de Automação Serverless:** Um backend com API Gateway e funções Lambda para orquestrar o ciclo de vida da instância EC2 (start/stop) de forma assíncrona.
3.  **Sensor de Inatividade em Tempo Real:** Um mecanismo orientado a eventos que detecta a saída do último jogador através dos logs do jogo, acionando uma sequência de desligamento inteligente com um período de carência.
4.  **Operações Seguras e Resilientes:** Gerenciamento seguro de credenciais, inicialização automatizada do servidor de jogo, monitoramento proativo e backups automáticos.

---

## 🏛️ Arquitetura da Solução

A arquitetura foi projetada priorizando o modelo serverless, orientação a eventos, eficiência de custos e robustez, utilizando diversos serviços gerenciados pela AWS. Abaixo detalho os fluxos principais:

### 1. Acesso ao Painel Web
**[DIAGRAMA: AWS1.png]**

O usuário acessa a URL pública fornecida pelo **Amazon CloudFront**. O CloudFront atua como CDN, entrega o conteúdo de forma otimizada e garante a conexão via **HTTPS**. Ele busca os arquivos estáticos do site (`index.html`, etc.) que estão hospedados no **Amazon S3**, configurado para *Static Website Hosting*.

### 2. Solicitação para Ligar Servidor (Assíncrono)
**[DIAGRAMA: AWS2.png]**

Ao clicar no botão "Ligar Servidor", o JavaScript no navegador envia uma requisição `POST /start-server` para a **Amazon API Gateway**. A API Gateway aciona a função **AWS Lambda** `vortex-start-server-function`. Esta Lambda *apenas* envia o comando `StartInstances` para a instância **Amazon EC2** correspondente e retorna imediatamente uma mensagem de "Comando recebido" para o frontend. A instância EC2 começa a iniciar em segundo plano.

### 3. Verificação de Status do Servidor (Polling)
**[DIAGRAMA: AWS3.png]**

Após receber a confirmação de que o comando de início foi enviado, o JavaScript no frontend inicia um *loop de polling*. A cada 10 segundos, ele envia uma requisição `GET /server-status` para a **API Gateway**. Esta, por sua vez, aciona a função **Lambda** `vortex-get-server-status-function`. Esta Lambda consulta o estado atual da instância **EC2** (`DescribeInstances`) e retorna o status (`pending`, `running`, `stopped`) e o IP público (se estiver `running`). O frontend atualiza a mensagem na tela com base nessa resposta e para o polling quando o status é `running` ou `stopped`.

### 4. Desligamento Automático do Servidor (Orientado a Eventos)
**[DIAGRAMA: AWS4.png]**

Quando o último jogador sai do servidor Minecraft (rodando no **EC2**), uma entrada é escrita no arquivo de log armazenado no disco **Amazon EBS**. O **CloudWatch Agent**, rodando no EC2, detecta essa linha e a envia para o **Amazon CloudWatch Logs**. Um **Filtro de Inscrição** configurado neste grupo de logs detecta o padrão "lost connection" e aciona instantaneamente a função **Lambda** `vortex-stop-server-function`.
A Lambda `stopServer` primeiro busca a senha RCON no **SSM Parameter Store**. Em seguida, ela usa o **SSM Run Command** para executar `mcrcon list` na instância **EC2** e verificar se o número de jogadores é realmente zero.
Se for zero, em vez de desligar imediatamente, a Lambda cria um agendamento único no **Amazon EventBridge Scheduler** para se re-executar em 5 minutos.
Após 5 minutos, o **EventBridge Scheduler** aciona a **Lambda** `stopServer` novamente. Ela repete a verificação de jogadores via **SSM Run Command**. Se o contador ainda for zero, a Lambda finalmente envia o comando `StopInstances` para o serviço **EC2**, desligando o servidor.

### 5. Monitoramento e Segurança Contínuos
**[DIAGRAMA: AWS5.png]**

Enquanto o **EC2** está rodando, o **CloudWatch Agent** e o próprio sistema enviam métricas (CPU, Rede, PlayerCount, etc.) para o **Amazon CloudWatch Metrics**. Um **Dashboard** no CloudWatch exibe essas métricas e logs de forma centralizada. **Alarmes** configurados no CloudWatch monitoram métricas como `CPUUtilization`; se um limite é excedido, o alarme aciona um **Tópico SNS**, que envia uma notificação por e-mail ao administrador. O **AWS Data Lifecycle Manager (DLM)** cria automaticamente snapshots (backups) do volume **EBS** da instância. O **AWS IAM** controla todas as permissões entre os serviços, garantindo que cada componente só possa acessar o que é necessário. O **SSM Parameter Store** armazena a senha RCON de forma segura, sendo consultado pela Lambda `stopServer` e pelo script no EC2 quando necessário.

---

## ✨ Funcionalidades Principais
* **Start On-Demand:** Inicia o servidor via interface web.
* **Status Assíncrono:** O painel informa o progresso da inicialização e exibe o IP dinâmico.
* **Desligamento por Evento:** Reage instantaneamente à saída do último jogador.
* **Período de Carência:** Timer de 5 minutos antes do desligamento final.
* **Custo Zero Ocioso:** Instância EC2 é desligada automaticamente.
* **Senha Segura:** Credencial RCON gerenciada pelo SSM Parameter Store.
* **Frontend Seguro:** Painel servido via HTTPS pelo CloudFront.
* **Autostart do Jogo:** Serviço `systemd` garante que o Minecraft inicie com o EC2.
* **Monitoramento e Alertas:** Visibilidade via Dashboard e notificações proativas via SNS.
* **Backups Automáticos:** Recuperação de desastres garantida pelo DLM.

---

## 🛠️ Pilha Tecnológica
* **Computação:** AWS EC2 (t2.micro/configurável), AWS Lambda (Python 3.11+ com Boto3)
* **Rede:** Amazon VPC, Security Groups, Amazon API Gateway (HTTP API), Amazon CloudFront
* **Armazenamento:** Amazon S3 (Static Website Hosting), Amazon EBS
* **Monitoramento e Logs:** Amazon CloudWatch (Logs, Metrics, Alarms, Dashboards, Agent)
* **Automação e Gerenciamento:** Amazon EventBridge Scheduler, AWS Systems Manager (SSM) Run Command, AWS Systems Manager (SSM) Parameter Store (SecureString), AWS Data Lifecycle Manager (DLM)
* **Segurança:** AWS IAM (Roles, Policies, Relações de Confiança)
* **Notificações:** Amazon SNS
* **Servidor:** Linux (Amazon Linux 2023), `systemd`, `mcrcon`
* **Frontend:** HTML, CSS, JavaScript (Vanilla)
* **Outros:** Git, GitHub

---

## 🚀 Jornada de Desenvolvimento e Conceitos Chave

Este projeto evoluiu iterativamente, refletindo desafios comuns no desenvolvimento em nuvem:

1.  **Fundação (EC2 e Controle Manual):** Começou com a configuração da instância **EC2** principal para hospedar o servidor Minecraft em um volume **EBS**. A operação inicial era manual via SSH.
2.  **Introduzindo Automação (Backend Serverless):** A necessidade de automação levou à construção do backend serverless.
    * **API Gateway** foi implementada como o ponto de entrada HTTP seguro.
    * Funções **Lambda** (`startServer`, `getStatus`) foram desenvolvidas em Python usando Boto3 para interagir com a API do EC2 (`StartInstances`, `DescribeInstances`).
    * **Desafio:** Encontrou-se o limite de 30 segundos da API Gateway, forçando uma refatoração para uma **arquitetura assíncrona**. O frontend (`index.html` no **S3**) foi atualizado para usar **polling via JavaScript** contra o endpoint `/server-status`.
3.  **Entrega do Frontend (CloudFront e S3):** O frontend `index.html` foi hospedado no **S3** configurado para hospedagem de site estático. O **CloudFront** foi adicionado como CDN para fornecer **HTTPS**, melhorar a performance global e aumentar a segurança.
    **Desafio:** Exigiu configuração cuidadosa do **CORS** na API Gateway para permitir requisições do domínio do CloudFront.
4.  **Desligamento Inteligente (Lógica Orientada a Eventos):** A ideia inicial de verificações periódicas foi substituída por uma abordagem mais eficiente orientada a eventos.
    * O **CloudWatch Agent** foi instalado no EC2 para transmitir os logs do Minecraft (`latest.log` no **EBS**) para o **CloudWatch Logs**.
    * Um **Filtro de Inscrição de Logs** foi criado para acionar a **Lambda** `stopServer` instantaneamente ao detectar o evento "lost connection".
    * **Desafio:** A depuração de permissões do **IAM** (`iam:PassRole`, `lambda:InvokeFunction`) e políticas de confiança entre serviços (Lambda <-> Scheduler) foi crítica para o fluxo orientado a eventos funcionar.
    * A Lambda `stopServer` foi aprimorada para realizar uma verificação de jogadores em tempo real usando **SSM Run Command** para executar `mcrcon list` na instância EC2.
    * Para evitar desligamentos prematuros, um período de carência de 5 minutos foi implementado usando o **EventBridge Scheduler**, onde a Lambda agenda a si mesma para uma verificação final.
5.  **Segurança e Robustez:**
    * A senha RCON foi protegida usando **SSM Parameter Store** (`SecureString`), removendo-a do código na Lambda e no script do EC2. O código foi refatorado para buscar o segredo em tempo de execução via `ssm:GetParameter`.
    * Um **serviço `systemd`** foi criado na instância EC2 para garantir que o servidor Minecraft inicie automaticamente e de forma confiável no boot, eliminando passos manuais via SSH.
    * **Roles e Políticas do IAM** foram refinadas iterativamente para aderir ao princípio do menor privilégio.
    * **Dashboards do CloudWatch**, **Alarmes** e notificações via **SNS** foram configurados para visibilidade operacional.
    * O **DLM** foi configurado para backups automatizados de snapshots do **EBS**.

---

## 🤔 Desafios e Aprendizados
* **Restrições de Recursos:** A implantação inicial na `t2.micro` levou a problemas de performance, exigindo troubleshooting (Status Checks, Screenshots do EC2) e otimização a nível de aplicação (parâmetro `view-distance` do Minecraft).
* **Timeouts de API:** Atingir o limite de 30 segundos da API Gateway necessitou uma mudança fundamental de arquitetura síncrona para assíncrona, utilizando polling no frontend.
* **Permissões e Confiança do IAM:** Depurar `iam:PassRole`, `lambda:InvokeFunction` e políticas de confiança entre serviços (Lambda <-> Scheduler) foi essencial para o fluxo orientado a eventos.
* **Debugging Serverless:** A dependência intensa dos Logs do CloudWatch provou ser fundamental para diagnosticar problemas dentro das funções Lambda e entender as interações entre os serviços.
* **Nuances dos Serviços AWS:** Aprendizado sobre requisitos específicos como `TimeoutSeconds` mínimo do SSM, detalhes da configuração CORS e a diferença entre vários principais de serviço AWS nas políticas do IAM.
