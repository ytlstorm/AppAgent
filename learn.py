import argparse
import datetime
import time

from scripts.cli_common import CommandRunner, ScriptCommand, build_common_args, normalize_app_name
from scripts.utils import print_with_color


WELCOME_MESSAGE = (
    "Welcome to the exploration phase of AppAgent!\nThe exploration phase aims at generating "
    "documentations for UI elements through either autonomous exploration or human demonstration. "
    "Both options are task-oriented, which means you need to give a task description. During "
    "autonomous exploration, the agent will try to complete the task by interacting with possible "
    "elements on the UI within limited rounds. Documentations will be generated during the process of "
    "interacting with the correct elements to proceed with the task. Human demonstration relies on "
    "the user to show the agent how to complete the given task, and the agent will generate "
    "documentations for the elements interacted during the human demo. To start, please enter the "
    "main interface of the app on your phone."
)
MODE_PROMPT = (
    "Choose from the following modes:\n1. autonomous exploration\n2. human demonstration\n"
    "Type 1 or 2."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="AppAgent - exploration phase",
    )
    parser.add_argument("--app")
    parser.add_argument("--root_dir", default="./")
    return parser.parse_args()


def ask_for_mode() -> str:
    print_with_color(MODE_PROMPT, "blue")
    while True:
        value = input().strip()
        if value in {"1", "2"}:
            return value


def ask_for_app_name() -> str:
    print_with_color("What is the name of the target app?", "blue")
    return normalize_app_name(input())


def create_demo_name(app: str) -> str:
    demo_timestamp = int(time.time())
    return datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")


def run_autonomous_exploration(*, app: str, root_dir: str) -> None:
    command = ScriptCommand(
        script_path="scripts/self_explorer.py",
        args=build_common_args(app=app, root_dir=root_dir),
    )
    CommandRunner.run(command)


def run_human_demonstration(*, app: str, root_dir: str) -> None:
    demo_name = create_demo_name(app)
    commands = [
        ScriptCommand(
            script_path="scripts/step_recorder.py",
            args=("--app", app, "--demo", demo_name, "--root_dir", root_dir),
        ),
        ScriptCommand(
            script_path="scripts/document_generation.py",
            args=("--app", app, "--demo", demo_name, "--root_dir", root_dir),
        ),
    ]
    CommandRunner.run_many(commands)


def main() -> None:
    args = parse_args()
    print_with_color(WELCOME_MESSAGE, "yellow")

    mode = ask_for_mode()
    app = normalize_app_name(args.app) if args.app else ask_for_app_name()

    if mode == "1":
        run_autonomous_exploration(app=app, root_dir=args.root_dir)
        return

    run_human_demonstration(app=app, root_dir=args.root_dir)


if __name__ == "__main__":
    main()
