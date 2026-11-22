# flatpak — установка и обновление переносимых приложений

## Назначение

Flatpak работает с источниками приложений и отдельными областями установки. В примерах используется пользовательская область. Системная установка обслуживает всех пользователей.

## Debian

Установи flatpak через APT. Команды далее предполагают, что у пользователя уже добавлен источник с именем flathub.

```bash
sudo apt install flatpak
flatpak remotes --user
flatpak search --user vlc
flatpak install --user flathub org.videolan.VLC
flatpak update --user
```

## Fedora

Установи flatpak через DNF, если пакет отсутствует. Источники системы и пользователя могут различаться.

```bash
sudo dnf install flatpak
flatpak remotes --user
flatpak list --user
flatpak update --user
```

## Arch Linux

Установи flatpak через pacman с полноценным обновлением. Для пользовательских приложений сохраняй --user.

```bash
sudo pacman -Syu flatpak
flatpak remotes --user
flatpak search --user vlc
flatpak update --user
```

## Источники

- [Debian](https://docs.flatpak.org/en/latest/flatpak-command-reference.html)
- [Fedora](https://docs.flatpak.org/en/latest/flatpak-command-reference.html)
- [Arch Linux](https://docs.flatpak.org/en/latest/flatpak-command-reference.html)
