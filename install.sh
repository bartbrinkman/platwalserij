#!/bin/sh
# Install on the Pi: dependencies + autostart at boot as a systemd user service.
#   git clone git@github.com:bartbrinkman/platwalserij.git && cd platwalserij && ./install.sh
# Update later:  git pull && systemctl --user restart platwals
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
PIN=${PIN:-17}

sudo apt-get install -y python3-pygame python3-gpiozero

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/platwals.service <<EOF
[Unit]
Description=Platwalserij sound
After=sound.target

[Service]
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/platwals.py --pin $PIN
Restart=on-failure

[Install]
WantedBy=default.target
EOF

sudo loginctl enable-linger "$USER"  # start at boot, without anyone logged in
systemctl --user daemon-reload
systemctl --user enable --now platwals
systemctl --user --no-pager status platwals
