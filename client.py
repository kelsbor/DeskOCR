import os
import sys
import subprocess
import socket
import json
import tkinter as tk
import tkinter.font as tkFont

RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
SOCKET_PATH = os.path.join(RUNTIME_DIR, "deskocr.sock")
IMAGE_PATH = os.path.join(RUNTIME_DIR, "deskocr.png")

def capturar_tela():
    session_type = os.environ.get("XDG_SESSION_TYPE", "x11")
    
    if session_type == "wayland":
        # Run slurp first securely, then pass to grim
        slurp_result = subprocess.run(["slurp"], capture_output=True, text=True)
        if slurp_result.returncode != 0:
            sys.exit(0)
            
        geometry = slurp_result.stdout.strip()
        resultado = subprocess.run(["grim", "-g", geometry, IMAGE_PATH])
    else:
        resultado = subprocess.run(["maim", "-s", IMAGE_PATH])
    
    if resultado.returncode != 0:
        sys.exit(0)

def consultar_daemon():
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_PATH)
        client.send(IMAGE_PATH.encode('utf-8'))
        
        # Recebe os dados em blocos
        resposta = b""
        while True:
            bloco = client.recv(4096)
            if not bloco:
                break
            resposta += bloco
            
        return json.loads(resposta.decode('utf-8'))
    except Exception as e:
        return {"erro": f"Falha ao conectar no Daemon: {str(e)}"}
    finally:
        client.close()
        if os.path.exists(IMAGE_PATH):
            os.remove(IMAGE_PATH)

def exibir_interface(dados):
    root = tk.Tk()
    root.title("DeskOCR")
    root.geometry("450x400")
    root.attributes("-topmost", True)
    
    # Use "sans" to let the OS fontconfig select the best CJK fallback
    fonte_base = ("sans", 12)
    
    text_area = tk.Text(root, wrap=tk.WORD, padx=20, pady=20, font=fonte_base, bg="#1e1e2e", fg="#cdd6f4")
    text_area.pack(expand=True, fill=tk.BOTH)

    if "erro" in dados:
        text_area.insert(tk.END, dados["erro"])
    else:
        text_area.insert(tk.END, f"{dados.get('frase_original', '')}\n", "titulo")
        text_area.insert(tk.END, "─" * 40 + "\n\n", "linha")
        
        # Remove "italic" and rely on OS fallback font (sans)
        text_area.tag_config("titulo", font=("sans", 16, "bold"), foreground="#f38ba8", justify="center")
        text_area.tag_config("linha", foreground="#45475a", justify="center")
        text_area.tag_config("termo", font=("sans", 14, "bold"), foreground="#89b4fa")
        text_area.tag_config("leitura", font=("sans", 12), foreground="#a6e3a1") # Italic removed

        for item in dados.get("detalhes", []):
            text_area.insert(tk.END, f"{item['termo']} ", "termo")
            text_area.insert(tk.END, f"[{item['leitura']}]\n", "leitura")
            text_area.insert(tk.END, f"{item['significado']}\n\n")

    root.clipboard_clear()
    root.clipboard_append(dados.get("frase_original", ""))
    text_area.config(state=tk.DISABLED)
    root.bind("<Escape>", lambda e: root.destroy())
    
    root.mainloop()

if __name__ == "__main__":
    capturar_tela()
    resultado_json = consultar_daemon()
    exibir_interface(resultado_json)