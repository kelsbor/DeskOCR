#!/bin/bash

APP_NAME="deskocr"
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share/$APP_NAME"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "Stopping and disabling the DeskOCR daemon..."
systemctl --user disable --now "${APP_NAME}-daemon.service" 2>/dev/null

echo "Removing systemd service file..."
rm -f "$SYSTEMD_DIR/${APP_NAME}-daemon.service"
systemctl --user daemon-reload

echo "Removing executable wrapper..."
rm -f "$BIN_DIR/$APP_NAME"

echo "Removing application files..."
rm -rf "$SHARE_DIR"

echo "Uninstallation complete."
echo "Note: Remember to manually remove the DeskOCR keyboard shortcut from your AwesomeWM rc.lua configuration."