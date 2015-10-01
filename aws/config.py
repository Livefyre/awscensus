import sys
import os

from pyyacc import parser

def get_envs(YAMLs=[]):
    """
    return a configuration env for each supplied yaml file.
    """
    base = os.path.join(os.path.dirname(__file__), 'app.yaml')

    if not YAMLs:
        raise Exception('AWS config yaml required.')

    ret = []
    for YAML in YAMLs:
        builder, config = parser.build(base, YAML)
        validate = builder.validate(config)
        if validate:
            sys.stderr.write(
                'insufficient config, missing:\n' +
                '\n'.join([(4*' ')+':'.join(x) for x in validate.iterkeys()]) +
                '\n')
            return 1
        ret.append(config)
    return ret

