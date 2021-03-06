"""Format (compressed) CSV file for import into an SQL database using Linux system commands.

- This script seems to run ~1.6 times faster than the `python` version.
"""
import logging
import os
import os.path as op

from kmtools import system_tools

logger = logging.getLogger(__name__)


def decompress(
        infile, sep='\t', na_values=None, extra_substitutions=None, use_tmp=False, outfile=None):
    """Decompress `infile` to produce a file with name `${infile}.tmp`.

    Parameters
    ----------
    outfile : str | None
        The name of the (decompressed) output file. If None, use `${infile}.tmp`.
    """
    ext = op.splitext(infile)[-1]
    if ext == '.gz':
        executable = 'gzip -dc'
    elif ext == '.bz2':
        executable = 'bz2 -dc'
    else:
        executable = 'cat'

    if (executable.strip() == 'cat' and
            (not na_values or na_values == ['\\N']) and
            (not extra_substitutions)):
        logger.debug("No need to process input file '{}'".format(infile))
        return infile

    if outfile is None:
        outfile = infile + '.tmp'
    if op.isfile(outfile):
        logger.debug("Decompressed file '{}' already exists!")
        if use_tmp:
            logger.debug("Using...")
            return outfile
        else:
            logger.debug("Removing...")
            os.remove(outfile)

    sed_command = get_sed_command(sep, na_values, extra_substitutions)

    system_command = (
        "{executable} '{infile}' {sed_commad} > '{outfile}'".format(
            executable=executable,
            infile=infile,
            sed_commad=('| ' + sed_command) if sed_command else '',
            outfile=outfile,
        )
    )
    logger.debug(system_command)
    # NB: sed is CPU-bound, no need to do remotely
    system_tools.run_command(system_command, shell=True)
    assert op.isfile(outfile)
    return outfile


def get_sed_command(sep='\t', na_values=None, extra_substitutions=None):
    """."""
    na_values = list(na_values) if na_values is not None else []
    extra_substitutions = list(extra_substitutions) if extra_substitutions is not None else []

    if '\\N' in na_values:
        na_values.remove('\\N')

    if not na_values and not extra_substitutions:
        return ''

    system_command_head = "sed "
    system_command_body = ""
    system_command_body += ''.join([r"-e '{}' ".format(x) for x in extra_substitutions])
    for na_value in na_values:
        if na_value and na_value in "$.*[\\]^'\"":
            na_value = '\{}'.format(na_value)
        else:
            na_value = system_tools.format_unprintable(na_value)
        system_command_body += (
            r"-e 's/{0}{1}{0}/{0}\\N{0}/g' "
            r"-e 's/{0}{1}{0}/{0}\\N{0}/g' "
            r"-e 's/^{1}{0}/\\N{0}/g' "
            r"-e 's/{0}{1}$/{0}\\N/g' "
            r"-e 's/{0}{1}\r$/{0}\\N/g' "
            .format(system_tools.format_unprintable(sep), na_value)
        )
    return system_command_head + system_command_body


def main(infile, outfile, sep='\t', na_values=(), extra_substitutions=()):
    if not na_values:
        na_values = ['', '\\N', '.', 'na']

    outfile = decompress(
        infile=infile,
        sep=sep,
        na_values=na_values,
        extra_substitutions=extra_substitutions,
        outfile=outfile)
    assert op.isfile(outfile)
    return 0


if __name__ == '__main__':
    import argparse
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--infile', type=str)
    args = parser.parse_args()
    if args.outfile is None:
        args.outfile = op.splitext(args.infile)[0] + '.tmp'
    main(args.infile)
