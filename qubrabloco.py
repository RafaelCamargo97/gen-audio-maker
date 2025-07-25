import os

# Caminhos
caminho_entrada = r"C:\Users\rafae\OneDrive\Área de Trabalho\Projetos2025\audiobook\Alice\blocos.txt"
caminho_saida = r"C:\Users\rafae\OneDrive\Área de Trabalho\Projetos2025\audiobook\Alice\blocks"

# Garante que a pasta de saída exista
os.makedirs(caminho_saida, exist_ok=True)

# Lê o conteúdo do arquivo de entrada
with open(caminho_entrada, "r", encoding="utf-8") as arquivo:
    conteudo = arquivo.read()

# Divide o conteúdo em blocos, usando quebras de linha duplas como separador
blocos = [bloco.strip() for bloco in conteudo.strip().split("\n\n") if bloco.strip()]

# Salva cada bloco em um arquivo separado
for i, bloco in enumerate(blocos, start=1):
    nome_arquivo = os.path.join(caminho_saida, f"block{i}.txt")
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(bloco)

print(f"{len(blocos)} blocos foram processados e salvos em: {caminho_saida}")
