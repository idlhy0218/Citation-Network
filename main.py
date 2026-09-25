"""
Citation Network Builder
========================
Version: 1.2.0

Entry Point:
- python main.py                             -> Desktop GUI (default)
- python main.py --cli                       -> Terminal interactive tree selector
- python main.py --collection "Folder Name"  -> Process folder directly in CLI
- python main.py --test                      -> Test API connections
"""
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Citation Network Builder")
    parser.add_argument('--collection', type=str, default=None,
                        help='Name of the collection to process in CLI mode')
    parser.add_argument('--test', action='store_true',
                        help='Test API connections in CLI mode')
    parser.add_argument('--cli', action='store_true',
                        help='Run in interactive terminal CLI mode')
    parser.add_argument('--no-obsidian', '--skip-obsidian', action='store_true',
                        dest='no_obsidian',
                        help='Skip Obsidian note generation (citation analysis only)')
    parser.add_argument('--gui', action='store_true',
                        help='Run in Desktop GUI mode (default)')
    args, _ = parser.parse_known_args()

    # Launch GUI if default (no explicit CLI flag or collection/test arguments provided)
    if not args.cli and not args.collection and not args.test:
        try:
            from src.gui import main as gui_main
            gui_main()
            return
        except Exception as e:
            print(f"Failed to start GUI mode ({e}). Falling back to CLI mode...")

    from src.cli import run_cli
    run_cli(args)


if __name__ == '__main__':
    main()
