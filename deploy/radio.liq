#!/usr/bin/env liquidsoap
# Quadrix Radio — Liquidsoap 2.x main script.
#
# Behavior:
#   1. Reads a per-station playlist .m3u (Django writes this file).
#   2. Listens for a "live" source on harbor mount `/live`.
#   3. When live is on, it takes over; otherwise the auto playlist plays.
#   4. Falls back to a single safety file if both fail.
#   5. Pushes the result to Icecast as /stream.

# ----- Globals -----
log.file.set(true)
log.file.path.set("/var/log/liquidsoap/radio.log")
settings.server.telnet.set(true)
settings.server.telnet.port.set(1234)
settings.server.telnet.bind_addr.set("0.0.0.0")

# Path to the auto-rotation playlist (one absolute path per line).
playlist_file = "/srv/playlists/main.m3u"
safety_file   = "/srv/playlists/safety.mp3"

# ----- Auto playlist -----
auto = playlist(
    id="main",
    reload_mode="watch",
    mode="normal",
    on_track=fun (m) -> log("auto track: #{m['filename']}"),
    playlist_file
)

# Skip files that fail to open instead of aborting the stream.
auto = mksafe(auto)

# ----- Live (DJ harbor) -----
# DJs push to icecast://source:<password>@radio.example.com:8000/live with BUTT/OBS.
# Liquidsoap reads the same Icecast /live mount via `input.harbor`.
live = input.harbor(
    "live",
    port=8001,
    password="change-me-source-pass",
    buffer=2.0,
    max=10.0
)

# Live wins when present.
radio = fallback(
    track_sensitive=false,
    transitions=[
        cross(duration=2., (fun (a,b) -> add([b, a]))),
        cross(duration=2., (fun (a,b) -> add([b, a]))),
    ],
    [live, auto, single(safety_file)]
)

# ----- Metadata for Django to read via `<station>.metadata`. -----
# Django expects telnet command `<slug>.metadata` to return the current title.
# `playlist(id="main")` already exposes commands `main.skip`, `main.reload`, etc.

# ----- Output -----
output.icecast(
    %mp3(bitrate=128, samplerate=44100, stereo=true),
    host="127.0.0.1",
    port=8000,
    mount="/stream",
    name="Quadrix Radio",
    description="Audio for logistics drivers",
    genre="Talk/Music",
    password="change-me-source-pass",
    radio
)
