vetor_a <- c(25.00, 32.20, 35.16, 37.32, 39.00, 40.40, 41.62, 42.70, 43.68, 44.57, 45.39, 46.16, 46.88, 47.56, 48.20, 48.81, 49.39, 49.95, 50.48, 50.99, 51.48, 51.96, 52.42, 52.86, 53.29, 53.71, 54.11, 54.51, 54.89, 55.27, 55.63, 55.99, 56.33, 56.67, 57.00, 57.32, 57.64, 57.95, 58.26, 58.56, 58.85, 59.14, 59.42, 59.70, 59.97, 60.24, 60.50, 60.76, 61.02, 61.27, 61.51, 61.76, 62.00, 62.23, 62.47, 62.70, 62.93, 63.16, 63.38, 63.60, 63.82, 64.04, 64.25, 64.46, 64.67, 64.88, 65.08, 65.29, 65.49, 65.69, 65.88, 66.08, 66.27, 66.46, 66.65, 66.84, 67.03, 67.21, 67.40, 67.58, 67.76, 67.94, 68.12, 68.30, 68.48, 68.65, 68.83, 69.00, 69.17, 69.35, 69.52, 69.69, 69.86, 70.03, 70.20, 70.37, 70.54, 70.70, 70.87, 71.04, 71.20, 71.37, 71.53, 71.70, 71.86, 72.02, 72.18, 72.34, 72.50, 72.66, 72.82, 72.98, 73.13, 73.29, 73.44, 73.60, 73.75, 73.90, 74.05, 74.20, 74.35, 74.50, 74.65, 74.80, 74.94, 75.09, 75.24, 75.38, 75.53, 75.67, 75.82, 75.96, 76.11, 76.25, 76.39, 76.54, 76.68, 76.82, 76.96, 77.10, 77.24, 77.38, 77.52, 77.66, 77.80, 77.94, 78.07, 78.21, 78.35, 78.49, 78.62, 78.76, 78.90, 79.03, 79.17, 79.31, 79.44, 79.58, 79.71, 79.85, 79.98, 80.12, 80.25, 80.39, 80.52, 80.66, 80.79, 80.92, 81.06, 81.19, 81.32, 81.46, 81.59, 81.72, 81.85, 81.99, 82.12, 82.25, 82.38, 82.51, 82.64, 82.77, 82.90, 83.03, 83.16, 83.29, 83.42, 83.55, 83.68, 83.80, 83.93, 84.06, 84.19, 84.31, 84.44, 84.57, 84.69, 84.82, 84.94, 85.07, 85.19, 85.32, 85.44, 85.57, 85.69, 85.81, 85.94, 86.06, 86.18, 86.30, 86.42, 86.54, 86.66, 86.78, 86.90, 87.02, 87.14, 87.26, 87.37, 87.49, 87.61, 87.72, 87.84, 87.95, 88.07, 88.18, 88.30, 88.41, 88.52, 88.64, 88.75, 88.86, 88.97, 89.08, 89.19, 89.30, 89.41, 89.52, 89.63, 89.74, 89.85, 89.96, 90.06, 90.17, 90.28, 90.38, 90.49, 90.60, 90.70, 90.81, 90.91, 91.02, 91.12, 91.22, 91.33, 91.43, 91.53, 91.63, 91.73, 91.83, 91.93, 92.03, 92.13, 92.23, 92.33, 92.42, 92.52, 92.62, 92.71, 92.81, 92.90, 93.00, 93.09, 93.18, 93.28, 93.37, 93.46, 93.55, 93.64, 93.73, 93.82, 93.91, 94.00, 94.09, 94.18, 94.27, 94.35, 94.44, 94.53, 94.62, 94.70, 94.79, 94.88, 94.96, 95.05, 95.13, 95.22, 95.30, 95.39, 95.47, 95.55, 95.63, 95.72, 95.80, 95.88, 95.96, 96.04, 96.12, 96.20, 96.28, 96.36, 96.44, 96.52, 96.60, 96.68, 96.75, 96.83, 96.91, 96.98, 97.06, 97.14, 97.21, 97.29, 97.36, 97.43, 97.51, 97.58, 97.65, 97.73, 97.80, 97.87, 97.94, 98.01, 98.08, 98.15, 98.22, 98.29, 98.36, 98.43, 98.50, 98.57, 98.63, 98.70, 98.77, 98.83, 98.90, 98.96, 99.03, 99.09, 99.15, 99.22, 99.28, 99.34, 99.40, 99.46, 99.52, 99.58, 99.65, 99.71, 99.75, 98.75, 100.25, 99.00, 100.50, 99.25, 100.75, 99.50, 101.00, 98.75, 100.25)



vetor_b <- c(1:length(vetor_a))
View(vetor_b)
View(vetor_a)

temp_frame <- data.frame(Tempo = vetor_b, Temperatura = vetor_a)

class(temp_frame)
View(temp_frame)
plot(temp_frame)




# Instale o pacote ggplot2 se ainda não o tiver
# install.packages("ggplot2")

# Carregue o pacote ggplot2
library(ggplot2)

# Supondo que seu dataframe 'temp_frame' já esteja carregado no R
# Se você quiser simular os dados para testar o código, pode usar:
# temp_frame <- data.frame(
#   Tempo = 1:13,
#   Temperatura = c(25.00, 32.20, 35.16, 37.32, 39.00, 40.40, 41.62, 42.70, 43.68, 44.57, 45.39, 46.16, 46.88)
# )

# Calcular a média e a mediana da temperatura
media_temperatura <- mean(temp_frame$Temperatura)


# Carregue o pacote ggplot2
library(ggplot2)

# Supondo que seu dataframe 'temp_frame' já esteja carregado no R

# Calcular apenas a média da temperatura (a mediana não é mais necessária para o gráfico, mas pode ser útil manter o cálculo se precisar dela para outra coisa)
media_temperatura <- mean(temp_frame$Temperatura)
# mediana_temperatura <- median(temp_frame$Temperatura) # <--- Esta linha pode ser removida ou comentada

# Criar o gráfico de evolução da temperatura com ggplot2
ggplot(data = temp_frame, aes(x = Tempo, y = Temperatura)) +
  geom_point() +
  geom_line() +
  # Adiciona uma linha horizontal para a Média da Temperatura
  geom_hline(yintercept = media_temperatura, color = "red", linetype = "dashed", size = 1) +
  # Linha da mediana removida ou comentada:
  # geom_hline(yintercept = mediana_temperatura, color = "blue", linetype = "dotted", size = 1) +
  # Títulos e rótulos
  labs(title = "Evolução da Temperatura ao Longo do Tempo",
       x = "Tempo",
       y = "Temperatura") +
  theme_minimal() +
  # Adicionar anotação de texto para o valor da média
  annotate("text", x = max(temp_frame$Tempo) * 0.8, y = media_temperatura + 3,
           label = paste("Média: ", round(media_temperatura, 2)), color = "red", size = 4)
# Anotação de texto da mediana removida ou comentada:
# annotate("text", x = max(temp_frame$Tempo) * 0.8, y = mediana_temperatura - 1,
#          label = paste("Mediana: ", round(mediana_temperatura, 2)), color = "blue", size = 4)