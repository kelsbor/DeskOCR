#!/bin/bash

APP_NAME="deskocr"
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share/$APP_NAME"
SYSTEMD_DIR="$HOME/.config/systemd/user"
VENV_PYTHON="$(pwd)/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $(pwd)/.venv"
    exit 1
fi

mkdir -p "$BIN_DIR" "$SHARE_DIR" "$SYSTEMD_DIR"

cp daemon.py "$SHARE_DIR/"
cp client.py "$SHARE_DIR/"
cp logo.ico "$SHARE_DIR/"

# Create executable wrapper
cat << 'EOF' > "$BIN_DIR/$APP_NAME"
#!/bin/bash
VENV_PY="VENV_PLACEHOLDER"
CLIENT_PY="CLIENT_PLACEHOLDER"
exec "$VENV_PY" "$CLIENT_PY" "$@"
EOF

sed -i "s|VENV_PLACEHOLDER|$VENV_PYTHON|g" "$BIN_DIR/$APP_NAME"
sed -i "s|CLIENT_PLACEHOLDER|$SHARE_DIR/client.py|g" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"

# Create Systemd Service
cat << EOF > "$SYSTEMD_DIR/${APP_NAME}-daemon.service"
[Unit]
Description=DeskOCR Daemon
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$SHARE_DIR
ExecStart=$VENV_PYTHON $SHARE_DIR/daemon.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${APP_NAME}-daemon.service"

echo "Installation complete. Executable available at: $BIN_DIR/$APP_NAME"