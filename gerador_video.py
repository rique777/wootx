import openai
import requests
from moviepy.editor import *
import os
import random
import string

# Configurações de API
openai.api_key = ""
eleven_api_key = ""
telegram_bot_token = ""

def gerar_nome_aleatorio():
    nome = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + ".mp4"
    print(f"Nome do vídeo gerado: {nome}")
    return nome

def buscar_dados_usuarios():
    print("Buscando dados dos usuários...")
    response = requests.get("https://bufit.cloud/robo/retorno.php")
    if response.status_code == 200:
        print("Dados dos usuários obtidos com sucesso.")
        return response.json()
    else:
        print("Erro ao buscar dados dos usuários:", response.json())
        return []

# Função para gerar uma história para um vídeo curto de 30 segundos
def gerar_historia(roteiro, estilo):
    print(f"Gerando história para o roteiro: {roteiro} com estilo: {estilo}")
    prompt = f"Crie uma história muito curta baseada no seguinte roteiro: '{roteiro}' para um vídeo de apenas 30 segundos, "
    prompt += f"ilustrada no estilo de '{estilo}'. A história deve ter início, meio e fim claros e ser adequada para um vídeo curto nao escreva no texto comeo meio e fim."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    historia = response.choices[0].message['content'].strip()
    print(f"História gerada: {historia}")
    return historia

# Função para gerar descrição de imagens com base no roteiro e estilo
def gerar_descricao_imagem(roteiro, estilo):
    print(f"Gerando descrição de imagem para o roteiro: {roteiro} com estilo: {estilo}")
    prompt = f"Quais elementos seriam ideais para ilustrar o seguinte roteiro: '{roteiro}' no estilo '{estilo}'?"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    descricao = response.choices[0].message['content'].strip()
    print(f"Descrição gerada: {descricao}")
    return descricao

# Função para buscar imagens com base na descrição gerada pela DALL-E 3
def buscar_imagens(roteiro, estilo):
    print(f"Buscando imagens para o roteiro: {roteiro} com estilo: {estilo}")
    descricao = gerar_descricao_imagem(roteiro, estilo)
    print("Descrição para gerar imagens:", descricao)
    imagens = []
    for i in range(5):
        response = openai.Image.create(
            model="dall-e-3",
            prompt=descricao,
            n=1,
            size="1024x1024"
        )
        img_url = response['data'][0]['url']
        img_path = f"imagem_{i}.jpg"
        img_data = requests.get(img_url).content
        with open(img_path, 'wb') as handler:
            handler.write(img_data)
        imagens.append(img_path)
        print(f"Imagem {i+1} gerada e salva como {img_path}.")
    return imagens

# Função para gerar narração com Eleven Labs em português brasileiro
def gerar_audio(historia, id_voz):
    print("Gerando áudio da narração em português brasileiro...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{id_voz}"
    headers = {"xi-api-key": eleven_api_key, "Content-Type": "application/json"}
    data = {
        "text": historia,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        },
        "voice_language": "pt-BR"  # Define o idioma para português brasileiro
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        audio_path = "narracao.mp3"
        with open(audio_path, 'wb') as file:
            file.write(response.content)
        print(f"Narração gerada e salva como {audio_path}.")
        return audio_path 
    else:
        print("Erro ao gerar narração:", response.json())
        return None

# Função para criar vídeo com duração total de 30 segundos, sincronizando as imagens
def criar_video(imagens, audio):
    print("Criando vídeo com as imagens e áudio...")
    duracao_imagem = 30 / len(imagens)  # Calcula a duração de cada imagem para totalizar 30 segundos
    clips = [ImageClip(img).set_duration(duracao_imagem) for img in imagens]
    video = concatenate_videoclips(clips, method="compose")
    audio_background = AudioFileClip(audio).volumex(1.0)
    video = video.set_audio(audio_background)
    video_name = gerar_nome_aleatorio()
    video.write_videofile(video_name, fps=24)
    print(f"Vídeo criado: {video_name}")
    return video_name

# Função para enviar vídeo pelo Telegram
def enviar_telegram(video_path, telegram_id):
    print(f"Enviando vídeo para Telegram, ID: {telegram_id}...")
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendVideo"
    with open(video_path, 'rb') as video_file:
        response = requests.post(url, data={"chat_id": telegram_id}, files={"video": video_file})
    if response.status_code == 200:
        print(f"Vídeo enviado para {telegram_id}")
    else:
        print(f"Erro ao enviar vídeo para {telegram_id}: {response.json()}")

# Função para limpar arquivos temporários
def limpar_arquivos(arquivos):
    print("Limpando arquivos temporários...")
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            os.remove(arquivo)
            print(f"Arquivo {arquivo} removido.")

# Função para atualizar o campo 'processado' no banco de dados via user.php
def atualizar_processado(usuario):
    url = "https://bufit.cloud/robo/user.php"
    data = {"usuario": usuario}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print(f"Processado atualizado para o usuário: {usuario}")
    else:
        print(f"Erro ao atualizar processado para o usuário {usuario}: {response.json()}")

# Execução principal
print("Iniciando o gerador de vídeos...")
usuarios = buscar_dados_usuarios()
for usuario in usuarios:
    tema = usuario['tema']
    estilo = usuario.get('estilo', '')
    telegram_id = usuario['telegram']
    roteiro = usuario['roteiro']
    id_voz = usuario['voz']
    print(f"\nProcessando usuário: {usuario}")
    
    # Gerar conteúdo
    historia = gerar_historia(roteiro, estilo)
    imagens = buscar_imagens(roteiro, estilo)
    audio = gerar_audio(historia, id_voz)
    video = criar_video(imagens, audio)

    # Enviar vídeo pelo Telegram
    enviar_telegram(video, telegram_id)

    # Atualizar o campo processado
    atualizar_processado(usuario['usuario'])

    # Limpar arquivos temporários
    limpar_arquivos(imagens + [audio, video])

print("Processo concluído.")

