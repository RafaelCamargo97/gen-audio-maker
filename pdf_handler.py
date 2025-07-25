import os
import re
from PyPDF2 import PdfReader

# Caminhos de entrada e saída
pasta_entrada = r"C:\Users\rafae\PycharmProjects\gen-audio-maker\text-input"
pasta_saida = r"C:\Users\rafae\PycharmProjects\gen-audio-maker\audio-input"
limite = 1000

# Função para encontrar o primeiro PDF na pasta
def encontrar_pdf(pasta):
    for arquivo in os.listdir(pasta):
        if arquivo.lower().endswith(".pdf") or arquivo.lower().endswith(".txt"):
            return os.path.join(pasta, arquivo)
    raise FileNotFoundError("Nenhum arquivo encontrado na pasta de entrada.")

# Função para extrair texto do PDF
def extrair_texto_pdf(caminho_pdf):
    reader = PdfReader(caminho_pdf)
    texto = ""
    for pagina in reader.pages:
        texto += pagina.extract_text() + "\n"
    return texto

# Função para dividir o texto em blocos de até 4000 caracteres sem cortar frases
def dividir_em_blocos(texto, limite):
    blocos = []
    frases = re.split(r'(?<=[\.\!\?])\s+', texto)
    bloco_atual = ""

    for frase in frases:
        if len(bloco_atual) + len(frase) + 1 <= limite:
            bloco_atual += frase + " "
        else:
            blocos.append(bloco_atual.strip())
            bloco_atual = frase + " "

    if bloco_atual:
        blocos.append(bloco_atual.strip())

    return blocos

# Função para salvar os blocos em arquivos .txt numerados corretamente
def salvar_blocos(blocos, pasta_destino):
    os.makedirs(pasta_destino, exist_ok=True)
    for i, bloco in enumerate(blocos, start=1):
        nome_arquivo = f"block{i}.txt"
        caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(bloco)

# Execução do processo
def processar_pdf_para_txt():
    try:
        caminho_pdf = encontrar_pdf(pasta_entrada)
        print(f"PDF encontrado: {caminho_pdf}")
        texto = extrair_texto_pdf(caminho_pdf)
        blocos = dividir_em_blocos(texto, limite=limite)
        salvar_blocos(blocos, pasta_saida)
        print(f"{len(blocos)} blocos salvos com sucesso em '{pasta_saida}'")
    except Exception as e:
        print(f"Erro: {e}")

# Rodar
if __name__ == "__main__":
    processar_pdf_para_txt()
