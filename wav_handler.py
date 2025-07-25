import os
import re
from pydub import AudioSegment

# Caminhos
pasta_audio = r"C:\Users\rafae\PycharmProjects\gen-audio-maker\audio-output"
pasta_saida = os.path.join(pasta_audio, "whole-audiobook")
os.makedirs(pasta_saida, exist_ok=True)  # Garante que a subpasta exista

# Regex para identificar e extrair o número do nome do arquivo
padrao_arquivo = re.compile(r"block(\d+)\.wav")

# Lista e filtra arquivos .wav que seguem o padrão blockX.wav
arquivos = [
    f for f in os.listdir(pasta_audio)
    if padrao_arquivo.match(f)
]

# Ordena os arquivos com base no número no nome
arquivos_ordenados = sorted(
    arquivos,
    key=lambda nome: int(padrao_arquivo.match(nome).group(1))
)

# --- AJUSTE AQUI ---
# Cria uma pausa de 0.5 segundos (500 milissegundos)
# É mais eficiente criar o objeto da pausa uma vez, fora do loop.
pausa = AudioSegment.silent(duration=350)
# --- FIM DO AJUSTE ---

# Concatena os arquivos de áudio
audiobook = AudioSegment.empty()

for nome_arquivo in arquivos_ordenados:
    caminho_arquivo = os.path.join(pasta_audio, nome_arquivo)
    trecho = AudioSegment.from_wav(caminho_arquivo)

    # --- AJUSTE AQUI ---
    # Adiciona a pausa antes de cada trecho de áudio
    audiobook += pausa + trecho
    # --- FIM DO AJUSTE ---

# Salva o arquivo final
caminho_saida_final = os.path.join(pasta_saida, "whole_audiobook.wav")
audiobook.export(caminho_saida_final, format="wav")

print(f"Audiobook concatenado salvo em: {caminho_saida_final}")