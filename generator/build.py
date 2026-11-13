"""Generate one crate's Rust sources and contract tests into Cargo's OUT_DIR."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

import generate


def write(path, content):
    path = Path(path)
    if path.exists() and path.read_text() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def render(crate):
    model = generate.build(generate.parse())
    problems = (['arity: ' + problem for problem in generate.check_arity(model)]
                + ['contract: ' + problem for problem in generate.check_contract(model)])
    if problems:
        raise ValueError('\n'.join(problems))
    prefix = Path(generate.ROOT) / 'crates' / crate
    outputs = {template: path for template, path in generate.OUTPUTS.items()
               if Path(path).is_relative_to(prefix)}
    return generate.render(model, outputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crate', required=True,
                        choices=['platform-api', 'platform-pyo3', 'platform-provider'])
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outputs = render(args.crate)
        prefix = Path(generate.ROOT) / 'crates' / args.crate
        for source, content in outputs.items():
            # include! expands inside a module, where inner doc comments are
            # invalid. Public item documentation remains unchanged.
            content = '\n'.join('//' + line[3:] if line.startswith('//!') else line
                                for line in content.split('\n'))
            write(args.out_dir / Path(source).relative_to(prefix), content)
        return 0
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
