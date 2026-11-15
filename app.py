import argparse
from pathlib import Path

from cybersos.app import ServingConfig, build_app, launch_app
from cybersos.app.app_assets import load_app_assets
from cybersos.app.demo_artifacts import prepare_demo_traces
from cybersos.app.evidence_content import EvidenceFiles


def main() -> None:
    parser = argparse.ArgumentParser(description='CyberSOS public recovery-planning demo')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--base-manifest', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--trained-traces', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--prepare-demos', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.prepare_demos:
        print(prepare_demo_traces(load_app_assets()))
        return
    demo = build_app(serving=ServingConfig(args.contract, args.base_manifest, args.adapter),
                     evidence=EvidenceFiles(trained=args.trained_traces, report=args.report))
    try:
        launch_app(demo, host=args.host, port=args.port, prevent_thread_lock=args.smoke)
    finally:
        if args.smoke:
            demo.close()
    if args.smoke:
        print('CyberSOS headless build, launch and close passed.')


if __name__ == '__main__':
    main()
