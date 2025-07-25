import os
from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    concatenate_videoclips, concatenate_audioclips
)

# --- CONFIGURAÇÕES ---
PASTA_MIDIA = r"C:\Users\rafae\PycharmProjects\gen-audio-maker\midia"
NOME_VIDEO_ENTRADA = "video.mp4"
NOME_AUDIO_ENTRADA = "audio.mp3"  # Pode ser .mp3, .wav, etc.
NOME_VIDEO_SAIDA = "video_final.mp4"
NOME_AUDIO_SAIDA = "audio_final.mp3"

DURACAO_LOOP_SEGUNDOS = 3600  # ou 10800 para 3 horas
TEMPO_CROSSFADE = 1  # segundos
# --- FIM DAS CONFIGURAÇÕES ---

# Caminhos
caminho_video = os.path.join(PASTA_MIDIA, NOME_VIDEO_ENTRADA)
caminho_audio = os.path.join(PASTA_MIDIA, NOME_AUDIO_ENTRADA)
caminho_saida_video = os.path.join(PASTA_MIDIA, NOME_VIDEO_SAIDA)
caminho_saida_audio = os.path.join(PASTA_MIDIA, NOME_AUDIO_SAIDA)

# Flags de existência
existe_video = os.path.exists(caminho_video)
existe_audio = os.path.exists(caminho_audio)

# Nenhum arquivo encontrado
if not existe_video and not existe_audio:
    print("Nenhum arquivo de vídeo ou áudio encontrado na pasta.")
    exit()

# Só áudio → processar apenas o áudio em loop com crossfade
if not existe_video and existe_audio:
    print(f"Apenas áudio encontrado: {caminho_audio}")
    try:
        audio = AudioFileClip(caminho_audio)
        duracao_original = audio.duration
        repeticoes = int(DURACAO_LOOP_SEGUNDOS / (duracao_original - TEMPO_CROSSFADE)) + 1
        print(f"Repetindo áudio {repeticoes} vezes com fade-in de {TEMPO_CROSSFADE} segundos.")

        clips_audio = [audio]
        for _ in range(repeticoes - 1):
            clips_audio.append(audio.audio_fadein(TEMPO_CROSSFADE))

        audio_final = concatenate_audioclips(clips_audio)
        audio_final = audio_final.subclip(0, DURACAO_LOOP_SEGUNDOS)
        audio_final.write_audiofile(caminho_saida_audio)

        print(f"Áudio final exportado para: {caminho_saida_audio}")
    except Exception as e:
        print("Erro ao processar o áudio.")
        print(f"Detalhe: {e}")
    exit()

# Vídeo existe → processar normalmente com ou sem áudio
try:
    print(f"Carregando vídeo de: {caminho_video}")
    video = VideoFileClip(caminho_video)

    repeticoes = int(DURACAO_LOOP_SEGUNDOS / (video.duration - TEMPO_CROSSFADE)) + 1
    print(f"Repetindo vídeo {repeticoes} vezes com crossfade de {TEMPO_CROSSFADE} segundos.")

    clips_video = [video]
    for _ in range(repeticoes - 1):
        clips_video.append(video.crossfadein(TEMPO_CROSSFADE))

    video_final = concatenate_videoclips(clips_video, method="compose", padding=-TEMPO_CROSSFADE)
    video_final = video_final.subclip(0, DURACAO_LOOP_SEGUNDOS)

except Exception as e:
    print("Erro ao processar o vídeo.")
    print(f"Detalhe: {e}")
    exit()

# Se também houver áudio → adicionar ao vídeo
if existe_audio:
    try:
        print(f"Carregando áudio de: {caminho_audio}")
        audio = AudioFileClip(caminho_audio)
        clips_audio = [audio]
        for _ in range(repeticoes - 1):
            clips_audio.append(audio.audio_fadein(TEMPO_CROSSFADE))
        audio_final = concatenate_audioclips(clips_audio)
        audio_final = audio_final.subclip(0, DURACAO_LOOP_SEGUNDOS)
        video_final = video_final.set_audio(audio_final)
    except Exception as e:
        print("Erro ao adicionar o áudio ao vídeo.")
        print(f"Detalhe: {e}")

# Exporta o vídeo final
print(f"Exportando vídeo final para: {caminho_saida_video}")
video_final.write_videofile(caminho_saida_video, codec="libx264", audio_codec="aac")

print("Processo concluído com sucesso!")
