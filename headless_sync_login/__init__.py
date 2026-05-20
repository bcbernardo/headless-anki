"""Headless AnkiWeb authentication/sync helper.

Controlled by environment variables:
- HEADLESS_ANKIWEB_LOGIN=1 enables login on startup
- HEADLESS_ANKIWEB_USERNAME / HEADLESS_ANKIWEB_PASSWORD provide credentials
- HEADLESS_ANKIWEB_SYNC_ON_START=1 triggers sync after login/when already authenticated
- HEADLESS_ANKIWEB_CONFLICT_ACTION=cancel|upload|download chooses full-sync conflict handling
"""
from __future__ import annotations

import functools
import os
import traceback

from aqt import gui_hooks, mw
from aqt.qt import QTimer


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _log(message: str) -> None:
    print(f"[headless-ankiweb] {message}", flush=True)


def _patch_conflict_dialogs() -> None:
    """Replace GUI-only full-sync prompts with env-controlled choices."""
    import aqt.sync as sync

    choice = os.environ.get("HEADLESS_ANKIWEB_CONFLICT_ACTION", "cancel").strip().lower()

    def choose_full_sync(mw_, out, on_done):
        server_usn = out.server_media_usn if mw_.pm.media_syncing_enabled() else None
        if out.required == out.FULL_DOWNLOAD:
            _log("server requires full download; proceeding without GUI prompt")
            return sync.full_download(mw_, server_usn, on_done)
        if out.required == out.FULL_UPLOAD:
            _log("server requires full upload; proceeding without GUI prompt")
            return sync.full_upload(mw_, server_usn, on_done)
        if choice == "upload":
            _log("sync conflict detected; HEADLESS_ANKIWEB_CONFLICT_ACTION=upload")
            return sync.full_upload(mw_, server_usn, on_done)
        if choice == "download":
            _log("sync conflict detected; HEADLESS_ANKIWEB_CONFLICT_ACTION=download")
            return sync.full_download(mw_, server_usn, on_done)
        _log("sync conflict detected; no upload/download selected, cancelling")
        return on_done()

    def confirm_download(mw_, server_usn, on_done):
        _log("full download confirmation suppressed for headless mode")
        return sync.full_download(mw_, server_usn, on_done)

    def confirm_upload(mw_, server_usn, on_done):
        _log("full upload confirmation suppressed for headless mode")
        return sync.full_upload(mw_, server_usn, on_done)

    sync.full_sync = choose_full_sync
    sync.confirm_full_download = confirm_download
    sync.confirm_full_upload = confirm_upload


def _sync_collection() -> None:
    if not _truthy("HEADLESS_ANKIWEB_SYNC_ON_START"):
        return
    import aqt.sync as sync

    if not mw or not mw.col:
        _log("cannot sync: main window/collection not ready")
        return
    if not mw.pm.sync_auth():
        _log("cannot sync: no AnkiWeb sync auth available")
        return

    _log("starting AnkiWeb sync")
    sync.sync_collection(mw, lambda: _log("AnkiWeb sync finished"))


def _login_then_maybe_sync() -> None:
    try:
        _patch_conflict_dialogs()
        if not mw or not mw.col:
            _log("main window/collection not ready")
            return

        username = os.environ.get("HEADLESS_ANKIWEB_USERNAME", "").strip()
        password = os.environ.get("HEADLESS_ANKIWEB_PASSWORD", "")

        if _truthy("HEADLESS_ANKIWEB_LOGIN"):
            if not username or not password:
                _log("HEADLESS_ANKIWEB_LOGIN=1 but username/password env vars are missing")
                return

            _log(f"attempting AnkiWeb login for {username!r}")

            def on_done(fut, username=username):
                try:
                    auth = fut.result()
                except Exception as exc:  # noqa: BLE001 - log and keep Anki alive
                    _log(f"AnkiWeb login failed: {exc}")
                    traceback.print_exc()
                    return
                mw.pm.set_sync_key(auth.hkey)
                mw.pm.set_sync_username(username)
                mw.pm.save()
                _log("AnkiWeb login succeeded; sync key stored in profile")
                _sync_collection()

            mw.taskman.with_progress(
                lambda: mw.col.sync_login(
                    username=username,
                    password=password,
                    endpoint=mw.pm.sync_endpoint(),
                ),
                functools.partial(on_done),
                parent=mw,
            )
        else:
            _log("HEADLESS_ANKIWEB_LOGIN not enabled; using existing sync auth if present")
            _sync_collection()
    except Exception as exc:  # noqa: BLE001
        _log(f"startup helper failed: {exc}")
        traceback.print_exc()


def _on_profile_opened() -> None:
    QTimer.singleShot(3000, _login_then_maybe_sync)


gui_hooks.profile_did_open.append(_on_profile_opened)
