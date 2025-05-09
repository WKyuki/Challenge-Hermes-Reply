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

