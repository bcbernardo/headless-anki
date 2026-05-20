# Headless Anki
Headless Anki with the AnkiConnect plugin installed.  
Useful in automation workflows.

The default user profile is as barebones as it can get.

The following volumes are exposed and can be mounted by the user:
- `/data`: Anki data (Profile, decks etc.).
- `/export`: Path that can be used for exporting Anki decks, e.g. using the AnkiConnect API.

## Usage
To run, execute:
```bash
docker run -d -p 8765:8765 -v $(pwd)/export:/export thisisnttheway/headless-anki:latest
```

To bring your own Anki profile, mount it on `/data` in the container:
```bash
docker run -d -v ~/.local/share/Anki2:/data thisisnttheway/headless-anki:latest
```

> [!WARNING]
> If you do bring your own profile, make sure that your AnkiConnect configuration doesn't have a listen address of `localhost`

> [!TIP] 
> Launch the container with the environment var `ANKICONNECT_WILDCARD_ORIGIN=1` to set `webCorsOriginList` in AnkiConnects config to `["*"]`.  
> **This will modify your existing config** if you bring your own profile!  Your existing config file will be backed up to `config.json_bak_ha` first, however.  
> - If this ENV var is unset/not equal to 0, this backup will be restored (if existing)

You can also use other QT platform plugins by setting the env var `QT_QPA_PLATFORM`:
```bash
docker run -e QT_QPA_PLATFORM="offscreen" ...
```

By default, Anki will be launched using `QT_QPA_PLATFORM="vnc"`.  
This will enable Anki to be accessed using a VNC viewer which might help with debugging, provided port `5900` is forwarded:  
![](images/vnc_gui.png)

## Building
To quickly build the image yourself, issue:
```bash
docker build --progress=plain . -t headless-anki:custom
```

Different versions of each component (Anki, QT, AnkiConnect) can be installed.  
Supply those versions as build flags:
```bash
docker build \
    --build-arg ANKICONNECT_VERSION=25.2.25.0 \
    --build-arg ANKI_VERSION=25.02.4 \
    --build-arg QT_VERSION=6 \
    -t headless-anki:custom \
    .
```

For available versions, refer to:
- [Anki GitHub releases](https://github.com/ankitects/anki/releases)
- [AnkiConnect releases](https://git.sr.ht/~foosoft/anki-connect/refs)

## Headless AnkiWeb login/sync

This fork adds a small startup add-on that can authenticate against AnkiWeb without opening the GUI login dialog.
It follows the Anki forum guidance of calling `mw.col.sync_login(...)` and storing the returned sync key and username in the profile.

Environment variables:

- `HEADLESS_ANKIWEB_LOGIN=1` — log in on startup using the variables below.
- `HEADLESS_ANKIWEB_USERNAME` — AnkiWeb email/username.
- `HEADLESS_ANKIWEB_PASSWORD` — AnkiWeb password.
- `HEADLESS_ANKIWEB_SYNC_ON_START=1` — start a sync after login, or using existing stored sync auth when login is disabled.
- `HEADLESS_ANKIWEB_CONFLICT_ACTION=cancel|upload|download` — choose how to resolve full-sync conflicts in headless mode. Default is `cancel` to avoid accidental data loss.

For persistent use, mount `/data` to a Docker volume or host directory. After the first successful login, Anki stores the sync key in the profile, so future starts can omit the password and use `HEADLESS_ANKIWEB_SYNC_ON_START=1` with the existing profile.

A convenience script is included for local deployment:

```bash
scripts/configure-and-run-ankiweb.sh
```

It prompts for the AnkiWeb password without echoing it, writes a `0600` env file at `~/.config/headless-anki/ankiweb.env`, and starts a restartable container bound to `127.0.0.1:8765`.

After confirming the first login succeeded and the sync key was stored, remove the password from the env file:

```bash
scripts/disable-ankiweb-password-env.sh
```

Then recreate/restart the container with `HEADLESS_ANKIWEB_LOGIN=0` and `HEADLESS_ANKIWEB_SYNC_ON_START=1` so future syncs use the stored profile auth instead of keeping the AnkiWeb password in the container environment.
