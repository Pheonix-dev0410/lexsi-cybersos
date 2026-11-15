from dataclasses import replace
from typing import Any

from cybersos.app.about_content import about_content, artifact_paths
from cybersos.app.app_assets import load_app_assets
from cybersos.app.evidence_content import EvidenceFiles, default_report
from cybersos.app.evidence_view import build_evidence_view
from cybersos.app.incident_view import build_incident_view
from cybersos.app.practice_view import build_practice_view
from cybersos.app.serving_policy import ServingConfig, load_serving_model


def build_app(*, serving: ServingConfig = ServingConfig(), evidence: EvidenceFiles | None = None) -> Any:
    import gradio as gr

    assets = load_app_assets()
    files = evidence or EvidenceFiles()
    if files.report is None:
        files = replace(files, report=default_report())
    with gr.Blocks(title='CyberSOS · Recovery planning', analytics_enabled=False,
                   delete_cache=(600, 1800)) as demo:
        gr.Markdown('# CyberSOS\nPlan your next recovery step from the access you still have. '
                    'No real account connection. No credentials needed.')
        with gr.Tab('Incident guidance'):
            build_incident_view(assets, load_serving_model(serving))
        with gr.Tab('Practice drill'):
            build_practice_view(assets)
        with gr.Tab('Evidence'):
            build_evidence_view(assets, files)
        with gr.Tab('About'):
            gr.Textbox(about_content(assets), label='Scope, versions and simulation boundaries',
                       interactive=False, lines=15)
            gr.File(artifact_paths(assets, files), file_count='multiple', interactive=False,
                    label='Download synthetic artifacts and reviewed configuration')
    demo.queue(max_size=16, default_concurrency_limit=1, api_open=False)
    return demo


def launch_app(demo: Any, *, host: str = '127.0.0.1', port: int | None = None,
               prevent_thread_lock: bool = False) -> Any:
    return demo.launch(server_name=host, server_port=port, share=False, debug=False,
                       show_error=False, run_history=False, enable_monitoring=False,
                       footer_links=[], state_session_capacity=64, max_threads=4,
                       prevent_thread_lock=prevent_thread_lock)
