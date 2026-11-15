import argparse
from pathlib import Path

from cybersos.evaluation.evaluation_config import load_evaluation_config
from cybersos.evaluation.results_report import report_results
from cybersos.evaluation.sft_residual_gate import report_sft_residuals
from cybersos.project_paths import CONFIGS_DIR, REPORTS_DIR


def serving_cost(text: str) -> tuple[str, float]:
    label, _, amount = text.partition('=')
    if not label or not amount:
        raise argparse.ArgumentTypeError('Use LABEL=AMOUNT, for example B1=12.50')
    return label, float(amount)


def main() -> int:
    parser = argparse.ArgumentParser(description='Report measured runs, paired uncertainty, or the SFT residual gate.')
    parser.add_argument('--runs', required=True, type=Path)
    parser.add_argument('--stage', choices=('results', 'sft-residuals'), default='results')
    parser.add_argument('--config', type=Path, default=CONFIGS_DIR / 'eval.yaml',
                        help='Supplies the bootstrap seed, repetitions and final case count.')
    parser.add_argument('--output', type=Path, default=REPORTS_DIR)
    parser.add_argument('--serving-cost', type=serving_cost, action='append', default=[],
                        help='Actual serving bill for one policy on this workload, as LABEL=AMOUNT.')
    parser.add_argument('--remaining-seconds', type=float)
    args = parser.parse_args()
    try:
        config = load_evaluation_config(args.config)
        if args.stage == 'results':
            result = report_results(args.runs, args.output, config, serving_costs=dict(args.serving_cost))
        else:
            result = report_sft_residuals(args.runs, args.output, remaining_seconds=args.remaining_seconds,
                                          final_case_count=config.case_count)
    except (OSError, ValueError, RuntimeError, ImportError, KeyError) as error:
        parser.exit(1, f'report failed: {error}\n')
    print(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
