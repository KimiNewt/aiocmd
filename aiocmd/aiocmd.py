import asyncio
import inspect
import signal

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

try:
    from prompt_toolkit.completion.nested import NestedCompleter
except ImportError:
    from aiocmd.nested_completer import NestedCompleter
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop


class ExitPromptException(Exception):
    pass


class CommandInterruptedException(Exception):
    pass


class PromptToolkitCmd:
    ATTR_START = "do_"
    prompt = "$ "
    doc_header = "Documented commands:"
    aliases = {"?": "help", "exit": "quit"}

    def __init__(self, ignore_sigint=True):
        use_asyncio_event_loop()
        self.completer = self._make_completer()
        self.session = None
        self._ignore_sigint = ignore_sigint
        self._currently_running_task = None

    async def run(self):
        if self._ignore_sigint:
            asyncio.get_event_loop().add_signal_handler(signal.SIGINT, self._sigint_handler)
        self.session = PromptSession(enable_history_search=True, key_bindings=self._get_bindings())
        try:
            with patch_stdout():
                await self._run_prompt_forever()
        finally:
            if self._ignore_sigint:
                asyncio.get_event_loop().remove_signal_handler(signal.SIGINT)
            self._on_close()

    async def _run_prompt_forever(self):
        while True:
            try:
                result = await self.session.prompt(self.prompt, async_=True, completer=self.completer)
            except EOFError:
                return

            if not result:
                continue
            args = result.split()
            if args[0] in self.command_list:
                try:
                    self._currently_running_task = asyncio.ensure_future(
                        self._run_single_command(args[0], args[1:]))
                    await self._currently_running_task
                except CommandInterruptedException:
                    print()
                    continue
                except ExitPromptException:
                    return
            else:
                print("Command %s not found!" % args[0])

    def _sigint_handler(self):
        if self._currently_running_task:
            self._currently_running_task.set_exception(CommandInterruptedException)

    def _get_bindings(self):
        bindings = KeyBindings()
        bindings.add("c-c")(lambda event: self._interrupt_handler(event))
        return bindings

    async def _run_single_command(self, command, args):
        command_real_args = self._get_command_args(command)
        if len(command_real_args) != len(args):
            print("Bad command args. Usage: %s %s" % (command, " ".join(command_real_args)))
            return

        try:
            com_func = self._get_command(command)
            if asyncio.iscoroutinefunction(com_func):
                await com_func(*args)
            else:
                com_func(*args)
            return
        except (ExitPromptException, CommandInterruptedException):
            raise
        except Exception as ex:
            print("Command failed: ", ex)

    def _interrupt_handler(self, event):
        event.cli.current_buffer.text = ""

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
            command = command + " " + "".join(["<%s>" % arg for arg in self._get_command_args(command)])
            print('%-30s%s' % (command, command_doc or ""))

    def do_quit(self):
        """Exit the prompt"""
        raise ExitPromptException()

    def _on_close(self):
        """Optional hook to call on closing the cmd"""
        pass
