import argparse

from scripts.cli_common import CommandRunner, ScriptCommand, build_common_args, normalize_app_name
from scripts.utils import print_with_color


WELCOME_MESSAGE = (
    "Welcome to the deployment phase of AppAgent!\nBefore giving me the task, you should first tell me "
    "the name of the app you want me to operate and what documentation base you want me to use. I will "
    "try my best to complete the task without your intervention. First, please enter the main interface "
    "of the app on your phone and provide the following information."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="AppAgent - deployment phase",
    )
    parser.add_argument("--app")
    parser.add_argument("--root_dir", default="./")
    return parser.parse_args()


def ask_for_app_name() -> str:
    print_with_color("What is the name of the target app?", "blue")
    return normalize_app_name(input())


def main() -> None:
    args = parse_args()
    print_with_color(WELCOME_MESSAGE, "yellow")

    app = normalize_app_name(args.app) if args.app else ask_for_app_name()

    command = ScriptCommand(
        script_path="scripts/task_executor.py",
        args=build_common_args(app=app, root_dir=args.root_dir),
    )
    CommandRunner.run(command)


if __name__ == "__main__":
    main()
