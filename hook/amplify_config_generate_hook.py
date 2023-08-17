import sceptre.resolvers.stack_attr
from sceptre.exceptions import InvalidHookArgumentTypeError
from sceptre.hooks import Hook

from hook.amplify_config_builder import AmplifyConfigBuilder

PREFIX = "prefix"

AMPLIFY_CONFIG = "amplify_config"

FORMAT = "format"

AVAILABLE_FORMATS = ["json", "dart"]


class AmplifyConfigGenerateHook(Hook):
    """
    The following instance attributes are inherited from the parent class Hook.

    Parameters
    ----------
    argument: str
        The argument is available from the base class and contains the
        argument defined in the Sceptre config file (see below)
    stack: sceptre.stack.Stack
         The associated stack of the hook.
    """

    def run(self):
        """
        run is the method called by Sceptre. It should carry out the work
        intended by this hook.

        To use instance attribute self.<attribute_name>.

        Examples
        --------
        self.argument -- path to amplify config
        self.stack_config

        """
        if not self.argument:
            raise Exception(InvalidHookArgumentTypeError)

        prefix = self.argument.get(PREFIX)
        if not prefix:
            raise Exception(InvalidHookArgumentTypeError)

        amplify_config = self.argument.get(AMPLIFY_CONFIG)
        if not amplify_config:
            raise Exception(InvalidHookArgumentTypeError)

        format = self.argument.get(FORMAT, "json")
        if format not in AVAILABLE_FORMATS:
            raise Exception(InvalidHookArgumentTypeError)

        if isinstance(prefix, sceptre.resolvers.stack_attr.StackAttr):
            prefix.stack = self.stack
            prefix = prefix.resolve()

        builder = AmplifyConfigBuilder(self.stack.connection_manager, prefix)
        config = builder.build()

        with open(amplify_config, "w") as f:
            json_out = config.model_dump_json(indent=4)
            if format == "dart":
                f.write(f"const amplifyconfig = '''\n{json_out}\n''';")
            else:
                f.write(json_out)

    def __init__(self, *args, **kwargs):
        super(AmplifyConfigGenerateHook, self).__init__(*args, **kwargs)
