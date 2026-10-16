"""Command-line personal-use prototype. Run with python -m app.main.

Supports multiline interactive input or --text for reproducible local demos.
No inputs are stored, transmitted, or submitted to a language model.
"""
import argparse
from .agents.personal_agent import PersonalAgent
from .evaluation.rubric import CommunicationContext
from .reports.report_generator import generate_report


def main(argv=None) -> int:
    """Collect a communication and optional context, then print a report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', help='Communication to evaluate; omit for interactive input.')
    parser.add_argument('--audience', default=None, help='Intended audience.')
    parser.add_argument('--purpose', default=None, help='Intended communication outcome.')
    args = parser.parse_args(argv)
    try:
        if args.text is None:
            print('Enter workplace communication. Finish with a blank line:')
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if not line.strip():
                    break
                lines.append(line)
            communication = '\n'.join(lines)
            if not communication.strip():
                raise ValueError('Communication must contain non-whitespace text.')
            audience = args.audience if args.audience is not None else input('Audience (optional): ')
            purpose = args.purpose if args.purpose is not None else input('Purpose (optional): ')
        else:
            communication = args.text
            audience, purpose = args.audience or '', args.purpose or ''
        report = PersonalAgent().evaluate(communication, CommunicationContext(audience, purpose))
    except (EOFError, KeyboardInterrupt):
        print('\nInput cancelled. For piped input, supply --audience and --purpose (empty values are allowed).')
        return 1
    except ValueError as error:
        parser.error(str(error))
    print(generate_report(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
