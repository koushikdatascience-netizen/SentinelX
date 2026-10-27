#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "run as root: bash install-deploy-user.sh < authorized-key.pub" >&2
  exit 1
fi
if id sentinelx-deploy >/dev/null 2>&1; then
  echo "sentinelx-deploy already exists; inspect it before changing its access" >&2
  exit 1
fi
IFS= read -r public_key
if [[ ! "$public_key" =~ ^ssh-ed25519[[:space:]]+[A-Za-z0-9+/=]+([[:space:]].*)?$ ]]; then
  echo "expected one OpenSSH Ed25519 public key on stdin" >&2
  exit 2
fi

useradd --system --create-home --home-dir /var/lib/sentinelx-deploy --shell /bin/bash sentinelx-deploy
passwd --lock sentinelx-deploy >/dev/null
chmod 711 /srv/sentinelx
install -d -o sentinelx-deploy -g sentinelx-deploy -m 700 /srv/sentinelx/incoming
install -d -o sentinelx-deploy -g sentinelx-deploy -m 700 /var/lib/sentinelx-deploy/.ssh
printf 'command="/usr/local/sbin/sentinelx-deploy-receive",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty %s\n' "$public_key" > /var/lib/sentinelx-deploy/.ssh/authorized_keys
chown sentinelx-deploy:sentinelx-deploy /var/lib/sentinelx-deploy/.ssh/authorized_keys
chmod 600 /var/lib/sentinelx-deploy/.ssh/authorized_keys

install -o root -g root -m 755 deploy/hostinger/ssh-receive.sh /usr/local/sbin/sentinelx-deploy-receive
install -o root -g root -m 755 deploy/hostinger/ssh-deploy-root.sh /usr/local/sbin/sentinelx-deploy
install -o root -g root -m 755 deploy/hostinger/backup.sh /usr/local/sbin/sentinelx-backup
install -o root -g root -m 644 deploy/hostinger/sentinelx-backup.service /etc/systemd/system/sentinelx-backup.service
install -o root -g root -m 644 deploy/hostinger/sentinelx-backup.timer /etc/systemd/system/sentinelx-backup.timer
printf '%s\n' 'sentinelx-deploy ALL=(root) NOPASSWD: /usr/local/sbin/sentinelx-deploy *' > /etc/sudoers.d/sentinelx-deploy
chmod 440 /etc/sudoers.d/sentinelx-deploy
visudo -cf /etc/sudoers.d/sentinelx-deploy
systemctl daemon-reload
systemctl enable --now sentinelx-backup.timer
printf '%s\n' 'Installed forced-command deploy account. The private key must be stored only as GitHub Environment secret HOSTINGER_SSH_KEY.'
