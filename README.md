# Challenge Hermes Reply

## FIAP CHALLENGE SMART MAINTENANCE SaaS

## 👨‍🎓 Integrantes: 
- Yuki Watanabe Kuramoto
- Ricardo Batah Leone
- Cayo Henrique Gomes do Amaral
- Guilherme Martins Ventura Vieira Romeiro
- Rodrigo de Melo Reinaux Porto

## 👩‍🏫 Professores:
### Tutor(a) 
- Lucas Gomes Moreira
### Coordenador(a)
- André Godoi

## Entregáveis

### Proposta de metodologia
A solução irá coletar dados de cada um dos principais parâmetros de funcionamento dos equipamentos (incluindo, mas não se limitando a: vibração, temperatura, som, alinhamento, nível de óleo) para avaliação da condição de operação das máquinas. 

A coleta dos dados será realizada através de sensores específicos para cada um dos parâmetros, conforme detalhado no item número do item abaixo. Os sensores serão controlados através de um microprocessador ESP32 e multiplexadores – caso haja necessidade, mais de um microprocessador poderá ser utilizado. Inicialmente serão usadas amostras sintéticas de dados. 

O armazenamento dos dados será realizado em banco de dados online utilizando banco de dados customizado para a aplicação e desenvolvido através do serviço AWS da Amazon. A opção pelo armazenamento em nuvem se deu em função do modelo de distribuição, o SaaS; e também visando à redução do custo com hardware e à facilidade de expansão do serviço. 

O pré-processamento e a análise de dados serão realizados utilizando a linguagem R em conjunto com o serviço AWS (através de um computador EC2 ), as integrações e construção do dashboard interativo serão realizadas em aplicação Python.

Quanto à análise dos dados em tempo real, será realizada integração do banco de dados com um Modelo de IA (através do computador em EC2) treinado para prever a necessidade de manutenção dos equipamentos. O desenvolvimento do modelo utilizará o Scikit-learn, Keras ou TensorFlow.
Ao final a solução irá disponibilizar um software capaz de realizar a predição de necessidade de manutenção das máquinas através dos dados coletados pelos sensores.

### Parâmetros selecionados para coleta via sensores:
- Vibração: indicador crítico de desgaste em rolamentos, desbalanceamento ou desalinhamento.
- Temperatura: aumentos de temperatura operacional podem levar ao desgaste prematuro, redução de eficiência e quebra dos equipamentos.
- Som (análise acústica): alterações na frequência sonora identificam vazamentos, folgas mecânicas ou problemas de pressão. Sensores detectam padrões anormais antes de falhas catastróficas.
- Alinhamento de eixos: desalinhamento causa desgaste assimétrico e aumento no consumo energético.
- Nível de óleo: redução do volume recomendado amplifica o atrito, elevando a temperatura, gerando desgaste desnecessário e redução da vida útil.

### Proposta de recursos a serem utilizados
1. Sensores:
   
| Parâmetro  | Sensor | Qtd por máquina |
| ------------- | ------------- |------------- |
| Vibração | Acelerômetro tri-axial | 2 a 4 (eixos, mancais) |
| Temperatura  | Termopar tipo K ou sensor infravermelho | 2 a 6 (mancais, motores) |
| Som | Microfone industrial de alta sensibilidade (decibelímetro) | 1 a 3 (áreas críticas) |
| Alinhamento | Sensores equipados com acelerômetro e giroscópio | 1 a 2 por máquina |
| Nível de óleo | Sensor ultrassônico ou magnético (ex: sensores de nível com saída 4-20 mA) | 1 a 3 (áreas críticas) |

2. Microprocessador ESP32.
3. Multiplexadores para conexão dos sensores ao(s) microprocessador(es).
4. Serviços AWS da Amazon: Armazenamento de dados e Computador EC2.
5. Modelo de IA preditivo.


[Diagrama challenge.pdf](https://github.com/user-attachments/files/20113233/Diagrama.chalenge.pdf)


## SPRINT 2 - FIAP CHALLENGE SMART MAINTENANCE SaaS

## Visão Geral 

Este projeto, parte do FIAP Challenge Smart Maintenance SaaS, foca no monitoramento de parâmetros essenciais para prever falhas em máquinas industriais. A medição da temperatura foi escolhida como parâmetro inicial devido à sua ampla aplicabilidade e por ser um indicador precoce de problemas mecânicos, elétricos ou de lubrificação.

O projeto utiliza um sensor MPU6050, que integra medição de temperatura, giroscópio e acelerômetro. Essa escolha permite uma futura expansão do projeto para incluir outras medições sem um aumento significativo de custos.

## Componentes Utilizados

* **ESP32:** Microcontrolador.
* **MPU6050:** Sensor de temperatura, giroscópio e acelerômetro.

## Esquema do Circuito

O circuito foi montado e simulado utilizando a plataforma WOKWI. O ESP32 está conectado ao sensor MPU6050 conforme o diagrama abaixo:

![Esquema do Circuito](https://github.com/SeuUsuario/SeuRepositorio/blob/main/docs/circuito.png?raw=true)


## Cenário Simulado

Para a simulação, optou-se por monitorar o funcionamento de uma máquina industrial durante um período determinado, realizando uma medição por segundo, totalizando até 370 medições.

Nesse cenário, a máquina inicia suas operações e atinge uma temperatura máxima, mantendo esse nível por aproximadamente 10 segundos até o final da medição.

Em lugar do painel de controle do sensor na plataforma de simulação a geração das as variações de temperatura, foi feita a partir de uma _array_ de dados pré-carregados no código. Essa abordagem simulou a uniformidade dos intervalos de medição de um sensor real.

Após as medições, os dados são compilados para exportação em um arquivo CSV, processo simulado pela impressão dos dados lidos peo sensor no monitor serial.

### Funcionamento da Simulação no WOKWI

#### Início da Simulação:

A simulação é iniciada no WOKWI Simulator, exibindo o boot do ESP32 e a solicitação de entrada para o tempo de leitura.

![Início da Simulação](https://github.com/SeuUsuario/SeuRepositorio/blob/main/docs/simulacao_inicio.png?raw=true)


#### Leitura dos Dados Sintéticos de Temperatura:

Durante a simulação, o sistema realiza as leituras dos dados de temperatura sintéticos (pré-carregados), exibindo o tempo e a temperatura correspondente no terminal. [cite_start]O total de amostras sintéticas disponíveis é de 370.

![Leitura dos Dados](https://github.com/SeuUsuario/SeuRepositorio/blob/main/docs/simulacao_leitura.png?raw=true)


#### Exportação das Leituras para Arquivo CSV:

Ao final das medições, os dados são "exportados" para um arquivo CSV. [cite_start]Essa exportação é simulada pela impressão contínua dos valores de temperatura no monitor serial até o fim do processo.

![Exportação CSV](https://github.com/SeuUsuario/SeuRepositorio/blob/main/docs/simulacao_exportacao.png?raw=true)


## Gráfico:

Para a análise dos dados, as leituras apresentadas no monitor serial foram salvas em um arquivo CSV. [cite_start]Posteriormente, esses dados foram importados para o RStudio, onde um gráfico de evolução da temperatura foi produzido.

O gráfico demonstra claramente a tendência de aquecimento da máquina. [cite_start]A linha tracejada vermelha representa a temperatura média de operação, que é de 80.21 °C. A elevada temperatura média de operação indica uma tendência ao sobreaquecimento da máquina.

![Gráfico de Evolução da Temperatura](https://github.com/SeuUsuario/SeuRepositorio/blob/main/docs/grafico_temperatura.png?raw=true)




