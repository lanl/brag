import os
from cmd import Cmd
from typing import Callable

from rich import print as rprint

PrintFunction = Callable[[str], None]


class BragREPL(Cmd):
    print_fn: PrintFunction
    prompt: str = "brag> "
    exit_message: str = "Exiting brag shell ..."
    _help_message: str = "For help, type: ? or help"
    ascii = "\n".join([
        r"    __                    ",
        r"   / /_  _________ _____ _",
        r"  / __ \/ ___/ __ `/ __ `/",
        r" / /_/ / /  / /_/ / /_/ / ",
        r"/_.___/_/   \__,_/\__, /  ",
        r"                 /____/   ",
    ])

    def default(self, query: str):
        self.print_fn(query)

    def postcmd(self, stop: bool, line: str):
        print()
        return stop

    def do_exit(self, _):
        """Exit shell."""
        print(self.exit_message)
        return True

    def do_EOF(self, _):
        """Exit on Ctrl+D."""
        print(self.exit_message)
        return True

    def do_clear(self, arg):
        """Clear the screen. Same as pressing Ctrl+L."""
        os.system("cls" if os.name == "nt" else "clear")

    def emptyline(self):
        """Do nothing when an empty line is entered"""
        pass

    def run(self, intro: str, print_fn: PrintFunction):
        """Handle Ctrl+C to avoid quitting the program"""
        # Print intro only once.
        rprint(f"[bold magenta]{self.ascii}")
        print(intro)
        rprint("[grey50]" + self._help_message)
        self.print_fn = print_fn

        while True:
            try:
                self.cmdloop()
                break  # Allows breaking out of loop if EOF is triggered.
            except KeyboardInterrupt:
                print(
                    "\n(Interrupted) Press Ctrl+D to exit or continue typing."
                )


class AskREPL(BragREPL):
    prompt = "brag-ask> "

    def help_refresh(self):
        print("To clear memory, type: !refresh")

    def help_cite(self):
        print("To show sources, type: !cite")
