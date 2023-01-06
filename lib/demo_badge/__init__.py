from .badge import Badge
from .expresslink import readline
from .hardware import *

def welcome_message():
    import supervisor
    from demo_badge.provisioning import run
    try:
        run()
    except KeyboardInterrupt as e:
        supervisor.enable_autoreload()
        raise KeyboardInterrupt

# used only in foundational lab modules
def send_command(uart, command, debug=True) -> str:
    c = command.strip() + "\n"
    print(">", command)
    uart.write(c.encode())
    return readline(uart, debug=debug)
