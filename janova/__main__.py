"""Interface texte : `python -m janova`. Fonctionne sur PC, sur téléphone (Termux) et sur un robot via SSH."""

from __future__ import annotations

import argparse

from janova import __version__
from janova.config import load_config
from janova.core import Janova


def main() -> None:
    parser = argparse.ArgumentParser(prog="janova", description="Noyau JANOVA")
    parser.add_argument("message", nargs="*", help="une demande unique (sinon mode conversation)")
    parser.add_argument("--home", help="dossier de JANOVA (par défaut JANOVA_HOME ou ~/.janova)")
    args = parser.parse_args()

    config = load_config(args.home)
    janova = Janova(config)
    if config.brain_autosync:
        janova.sync_brain()  # relit les notes que tu as pu modifier pendant que JANOVA dormait
    try:
        if args.message:
            print(janova.handle(" ".join(args.message)).text)
            return
        print(f"JANOVA {__version__} — mémoire : {config.home}\nTape /aide pour les commandes, Ctrl+C pour quitter.\n")
        while True:
            try:
                message = input("toi > ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            reply = janova.handle(message)
            if reply.text:
                print(f"janova [{reply.route}] > {reply.text}\n")
    finally:
        janova.close()


if __name__ == "__main__":
    main()
