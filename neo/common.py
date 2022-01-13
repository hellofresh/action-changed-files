import logging
import os
import argparse

class LoggingHandler(logging.StreamHandler):
    """
    A logging handler that outputs to stderr and formats messages for GitHub Actions
    see: https://docs.github.com/en/actions/learn-github-actions/workflow-commands-for-github-actions#setting-an-output-parameter
    """
    def emit(self, record):
        if "GITHUB_ACTIONS" in os.environ:
            if record.levelno == logging.DEBUG:
                record.levelname = "::debug"
            elif record.levelno == logging.INFO:
                record.levelname = "::notice"
            elif record.levelno == logging.WARNING:
                record.levelname = "::warning"
            elif record.levelno == logging.ERROR:
                record.levelname = "::error"
        super().emit(record)


def setup_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(message)s",
        handlers=[LoggingHandler()],
    )


# Courtesy of http://stackoverflow.com/a/10551190 with env-var retrieval fixed
class EnvDefault(argparse.Action):
    """An argparse action class that auto-sets missing default values from env
    vars. Defaults to requiring the argument."""

    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

# functional sugar for the above
def env_default(envvar):
    def wrapper(**kwargs):
        return EnvDefault(envvar, **kwargs)
    return wrapper

def strtobool (val):
    # from https://github.com/python/cpython/blob/main/Lib/distutils/util.py#L308
    # since distutils is scheduled for removal
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))