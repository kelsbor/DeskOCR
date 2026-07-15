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
from deep_translator import GoogleTranslator  # New Import

# path logic
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
SOCKET_PATH = os.path.join(RUNTIME_DIR, "deskocr.sock")

# Convert katakana to hiragana 
def katakana_para_hiragana(texto):
    """Converts Katakana output from Janome into standard Hiragana."""
    if not texto or texto == '*':
        return ""
    # Shifts the Unicode codepoint of Katakana characters to their Hiragana equivalents
    return "".join([chr(ord(ch) - 96) if 0x30A1 <= ord(ch) <= 0x30F6 else ch for ch in texto])

def iniciar_servidor_socket():
    print("Carregando modelos (IA, Tokenizer, Dicionário)...")
    mocr = MangaOcr()
    tokenizer = Tokenizer()
    jam = Jamdict()
    translator = GoogleTranslator(source='ja', target='en')
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
                
                # Extract and convert contextual reading from Janome
                leitura_contextual = katakana_para_hiragana(token.reading)
                
                if "記号" in classe or "助詞" in classe or "助動詞" in classe:
                    continue
                
                termo_busca = palavra_dicionario if palavra_dicionario != '*' else palavra_capturada
                resultado = jam.lookup(termo_busca)
                
                if resultado.entries:
                    entrada = resultado.entries[0]

                    # 1. Trust Janome's contextual reading first.
                    # 2. If Janome fails (returns empty), fallback to Jamdict's default dictionary reading.
                    # 3. If Jamdict also has no reading, fallback to the search term itself.

                    if leitura_contextual:
                        print("Using janome")
                        leitura = leitura_contextual
                    elif entrada.kana_forms:
                        print("Using Jamdict")
                        leitura = entrada.kana_forms[0].text
                    else:
                        leitura = termo_busca
                    
                    significados = []
                    for i, sense in enumerate(entrada.senses[:3], 1):
                        gloss_text = ", ".join([g.text for g in sense.gloss])
                        significados.append(f"{i}. {gloss_text}")
                    
                    significado_final = " | ".join(significados)

                    palavras_processadas.append({
                        "termo": termo_busca,
                        "leitura": leitura,
                        "significado": significado_final
                    })
            
            traducao_completa = translator.translate(texto_ocr)
            resposta = {
                "frase_original": texto_ocr,
                "traducao": traducao_completa,
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