import os
import sys
import json
import socket
import threading
import subprocess
import pystray
from PIL import Image, ImageDraw
from manga_ocr import MangaOcr
from janome.tokenizer import Tokenizer
from jamdict import Jamdict

# path logic
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
SOCKET_PATH = os.path.join(RUNTIME_DIR, "deskocr.sock")

def iniciar_servidor_socket():
    print("Carregando modelos (IA, Tokenizer, Dicionário)...")
    mocr = MangaOcr()
    tokenizer = Tokenizer()
    jam = Jamdict()
    print("Modelos carregados. Servidor pronto.")

    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(1)

    while True:
        conn, _ = server.accept()
        try:
            image_path = conn.recv(1024).decode('utf-8').strip()
            
            if not os.path.exists(image_path):
                conn.send(json.dumps({"erro": "Imagem não encontrada"}).encode('utf-8'))
                continue

            texto_ocr = mocr(image_path)
            tokens = tokenizer.tokenize(texto_ocr)
            palavras_processadas = []

            for token in tokens:
                palavra_capturada = token.surface
                palavra_dicionario = token.base_form
                classe = token.part_of_speech
                
                if "記号" in classe or "助詞" in classe or "助動詞" in classe:
                    continue
                
                termo_busca = palavra_dicionario if palavra_dicionario != '*' else palavra_capturada
                resultado = jam.lookup(termo_busca)
                
                if resultado.entries:
                    entrada = resultado.entries[0]
                    leitura = entrada.kana_forms[0].text if entrada.kana_forms else termo_busca
                    significado = entrada.senses[0].gloss[0].text if entrada.senses else ""
                    
                    palavras_processadas.append({
                        "termo": termo_busca,
                        "leitura": leitura,
                        "significado": significado
                    })
            
            resposta = {
                "frase_original": texto_ocr,
                "detalhes": palavras_processadas
            }
            conn.send(json.dumps(resposta, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            conn.send(json.dumps({"erro": str(e)}).encode('utf-8'))
        finally:
            conn.close()

# --- SYSTEM TRAY LOGIC ---

def on_capture(icon, item):
    """Executes the client script, whether installed or running locally."""
    caminho_instalado = os.path.expanduser("~/.local/bin/deskocr")
    
    # Fallback paths for local testing before installation
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_local_client = os.path.join(diretorio_atual, "client.py")
    python_exe = sys.executable # Uses the Python binary from your active .venv
    
    if os.path.exists(caminho_instalado):
        subprocess.Popen([caminho_instalado])
    elif os.path.exists(caminho_local_client):
        subprocess.Popen([python_exe, caminho_local_client])
    else:
        print("Erro: Cliente não encontrado.")

def on_quit(icon, item):
    """Safely shuts down the daemon."""
    icon.stop()
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)
    os._exit(0) # Forces the background thread to terminate

def iniciar_system_tray():
    
    image = Image.open("logo.ico")
    # Removed 'default=True'. 
    # Now, left/right clicking the icon will properly open the menu on AwesomeWM.
    menu = pystray.Menu(
        pystray.MenuItem('Capture Screen', on_capture),
        pystray.MenuItem('Quit DeskOCR', on_quit)
    )
    
    icon = pystray.Icon("deskocr", image, "DeskOCR", menu)
    icon.run()

if __name__ == "__main__":
    # Start the heavy socket server in a background thread
    server_thread = threading.Thread(target=iniciar_servidor_socket, daemon=True)
    server_thread.start()
    
    # Start the system tray in the main thread (blocks until 'Quit' is clicked)
    iniciar_system_tray()