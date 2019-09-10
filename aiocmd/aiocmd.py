import asyncio
import inspect

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

try:
    from prompt_toolkit.completion.nested import NestedCompleter
except ImportError:
    from aiocmd.nested_completer import NestedCompleter
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout


class ExitPromptException(Exception):
    pass


class PromptToolkitCmd:
    ATTR_START = "do_"
    PROMPT = "$ "
    doc_header = "Documented commands:"
    aliases = {"?": "help", "exit": "quit"}

    def __init__(self):
        use_asyncio_event_loop()
        self.completer = self._make_completer()

    async def run(self):
        session = PromptSession()
        while True:
            with patch_stdout():
                try:
                    result = await session.prompt(self.PROMPT, async_=True, completer=self.completer)
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    return
                except asyncio.CancelledError:
                    print("CANCELED")
                if not result:
                    continue
                args = result.split()
                if args[0] in self.command_list:
                    command_real_args = self._get_command_args(args[0])
                    if len(command_real_args) != len(args[1:]):
                        print("Bad command args. Usage: %s %s" % (args[0], " ".join(command_real_args)))
                        continue

                    try:
                        self._get_command(args[0])(*args[1:])
                    except ExitPromptException:
                        return
                    except Exception as ex:
                        print("Command failed: ", ex)
                else:
                    print("Command %s not found!" % args[0])

    def _make_completer(self):
        return NestedCompleter({com: self._completer_for_command(com) for com in self.command_list})

    def _completer_for_command(self, command):
        if not hasattr(self, "_%s_completions" % command):
            return WordCompleter([])
        return getattr(self, "_%s_completions" % command)()

    def _get_command(self, command):
        if command in self.aliases:
            command = self.aliases[command]
        return getattr(self, self.ATTR_START + command)

    def _get_command_args(self, command):
        return list(inspect.signature(self._get_command(command)).parameters.keys())

    @property
    def command_list(self):
        return [attr[len(self.ATTR_START):]
                for attr in dir(self) if attr.startswith(self.ATTR_START)] + list(self.aliases.keys())

    def do_help(self):
        print()
        print(self.doc_header)
        print("=" * len(self.doc_header))
        print()
        for command in sorted(self.command_list):
            command_doc = self._get_command(command).__doc__
            command_args = "".join(["<%s>" % arg for arg in self._get_command_args(command)])
            print("%s %s      %s" % (command, command_args, command_doc or ""))

    def do_quit(self):
        """Exit the prompt"""
        raise ExitPromptException()
