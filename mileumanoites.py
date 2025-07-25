import os
import re
import PyPDF2  # Biblioteca para ler arquivos PDF

# --- CONFIGURAÇÃO ---
# O script irá procurar o arquivo de entrada e salvar os contos nesta pasta.
# O 'r' antes da string é importante para que o Windows interprete o caminho corretamente.
DIRETORIO_TRABALHO = r"C:\Users\rafae\PycharmProjects\gen-audio-maker\text-input"

## ALTERAÇÃO ##
# Nome do arquivo único que conterá todos os contos.
NOME_ARQUIVO_SAIDA = "contos_compilados.txt"
# --------------------
def extrair_texto_do_arquivo(caminho_arquivo):
    """
    Extrai o texto de um arquivo .txt ou .pdf.
    Retorna uma string com o conteúdo completo.
    """
    texto_completo = ""
    print(f"Lendo o arquivo: {os.path.basename(caminho_arquivo)}...")
    try:
        if caminho_arquivo.lower().endswith('.txt'):
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                texto_completo = f.read()
        elif caminho_arquivo.lower().endswith('.pdf'):
            with open(caminho_arquivo, 'rb') as f:
                leitor_pdf = PyPDF2.PdfReader(f)
                for pagina in leitor_pdf.pages:
                    texto_extraido = pagina.extract_text()
                    if texto_extraido:
                        texto_completo += texto_extraido
        print("Leitura concluída com sucesso.")
        return texto_completo
    except Exception as e:
        print(f"Erro ao ler o arquivo {caminho_arquivo}: {e}")
        return None


def sanitizar_nome_arquivo(nome):
    """
    Remove caracteres inválidos de um nome de arquivo e limita seu tamanho.
    (Esta função não é mais usada para criar nomes de arquivo, mas pode ser útil no futuro)
    """
    # Remove caracteres que não são permitidos em nomes de arquivo no Windows
    nome = re.sub(r'[\\/*?:"<>|]', "", nome)
    # Limita o comprimento para evitar nomes de arquivo excessivamente longos
    return nome.strip()[:150]


def separar_contos(texto_completo):
    """
    Separa o texto em contos, identificando os títulos em maiúsculas.
    Retorna uma lista de dicionários, onde cada um contém o título e o conteúdo do conto.
    """
    contos = []
    linhas = texto_completo.split('\n')

    titulo_atual = None
    conteudo_atual = []

    print("Iniciando a separação por contos...")

    for linha in linhas:
        linha_strip = linha.strip()
        # Condição para identificar um título:
        # - A linha não está vazia.
        # - Todos os caracteres são maiúsculos.
        # - Não é apenas um número.
        # - Tem mais de 4 caracteres para evitar falsos positivos como "FIM".
        if linha_strip and linha_strip.isupper() and not linha_strip.isdigit() and len(linha_strip) > 4:
            # Se já temos um título e um conteúdo, salvamos o conto anterior
            if titulo_atual and conteudo_atual:
                contos.append({
                    "titulo": titulo_atual,
                    "conteudo": "\n".join(conteudo_atual).strip()
                })
                print(f"  - Conto identificado: {titulo_atual}")

            # Inicia um novo conto
            titulo_atual = linha_strip
            conteudo_atual = []
        else:
            # Adiciona a linha ao conteúdo do conto atual
            if titulo_atual:
                conteudo_atual.append(linha)

    # Adiciona o último conto que estava sendo processado
    if titulo_atual and conteudo_atual:
        contos.append({
            "titulo": titulo_atual,
            "conteudo": "\n".join(conteudo_atual).strip()
        })
        print(f"  - Conto identificado: {titulo_atual}")

    return contos


def main():
    """
    Função principal do script.
    """
    # Encontra o primeiro arquivo .txt ou .pdf no diretório
    caminho_arquivo_entrada = None
    for nome_arquivo in os.listdir(DIRETORIO_TRABALHO):
        if nome_arquivo.lower().endswith(('.txt', '.pdf')):
            caminho_arquivo_entrada = os.path.join(DIRETORIO_TRABALHO, nome_arquivo)
            break

    if not caminho_arquivo_entrada:
        print(f"ERRO: Nenhum arquivo .txt ou .pdf encontrado no diretório '{DIRETORIO_TRABALHO}'")
        return

    # Extrai o texto do arquivo
    texto_livro = extrair_texto_do_arquivo(caminho_arquivo_entrada)
    if not texto_livro:
        return

    # Separa o texto em contos
    lista_de_contos = separar_contos(texto_livro)

    if not lista_de_contos:
        print("Nenhum conto foi encontrado. Verifique se os títulos estão em MAIÚSCULAS.")
        return

    ## --- INÍCIO DA ALTERAÇÃO --- ##
    # A lógica de salvar arquivos foi completamente substituída.

    print(f"\n{len(lista_de_contos)} contos foram encontrados. Salvando todos em um único arquivo...")

    # Define o caminho completo para o arquivo de saída único
    caminho_arquivo_saida = os.path.join(DIRETORIO_TRABALHO, NOME_ARQUIVO_SAIDA)

    try:
        # Abre o arquivo de saída uma única vez em modo de escrita ('w')
        with open(caminho_arquivo_saida, 'w', encoding='utf-8') as f:
            # Itera sobre a lista de contos para escrevê-los no arquivo
            for i, conto in enumerate(lista_de_contos, 1):
                # Escreve um cabeçalho para o conto
                f.write(f"--- CONTO {i}: {conto['titulo']} ---\n\n")

                # Escreve o conteúdo do conto
                f.write(conto['conteudo'])

                # Adiciona um separador claro entre os contos, exceto após o último
                if i < len(lista_de_contos):
                    f.write("\n\n" + "=" * 70 + "\n\n")

        print(f"  - Todos os contos foram salvos com sucesso em: {NOME_ARQUIVO_SAIDA}")

    except Exception as e:
        print(f"ERRO ao salvar o arquivo {NOME_ARQUIVO_SAIDA}: {e}")

    ## --- FIM DA ALTERAÇÃO --- ##

    print("\nProcesso concluído com sucesso!")


# Executa o script
if __name__ == "__main__":
    main()