# civ5-caravan

Automatic clicker to retry Civ 5 caravan/cargo ship trade route.

The script in action in slow motion (1 second pause after mouse movement):

![civ5](https://raw.githubusercontent.com/mbachry/civ5-caravan/refs/heads/main/media/civ5route-slow.gif)

## Install

Linux and swaywm currently required. You also need ['grim'](https://sr.ht/~emersion/grim/) and `pipx`.

Clone the repo and install with:

```
pipx install .
```

Add a key binding in sway config, eg.:

```
bindsym $mod+t exec ~/.local/bin/civ5-caravan
```

Press `Super+t` when a caravan or cargo ship unit is active.
