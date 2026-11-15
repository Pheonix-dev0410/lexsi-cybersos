from cybersos.app.app_assets import AppAssets
from cybersos.app.demo_cases import DEMO_LABELS
from cybersos.app.evidence_content import EvidenceFiles, evidence_content, measured_report


def build_evidence_view(assets: AppAssets, files: EvidenceFiles) -> None:
    import gradio as gr

    gr.Markdown('Recorded simulations only. The selection stays on the same scenario and root when '
                'switching policies. Missing checkpoint generations are shown as “not run”. '
                'R is a rule baseline; it does not stand in for Tiny Aya base-model evidence.')
    scenario = gr.Dropdown(choices=[(label, key) for key, label in DEMO_LABELS.items()],
                           value='circular', label='Saved synthetic demo')
    selection = gr.Radio(choices=[('Baseline · R', 'baseline'), ('Trained checkpoint', 'trained')],
                          value='baseline', label='Saved policy run')
    initial = evidence_content(assets, files, 'circular', 'baseline')
    status = gr.Textbox(initial.status, label='Simulation outcome', interactive=False)
    identity = gr.Textbox(initial.identity, label='Saved run identity', interactive=False)
    with gr.Accordion('Expandable tool trace · raw proposals, guard decisions and simulated results', open=False):
        trace = gr.Code(initial.trace_text, language='json', interactive=False, label='Saved synthetic trace')
    with gr.Accordion('Measured evaluation table', open=True):
        gr.Textbox(measured_report(files), label='Saved report (missing measurements remain not run)',
                   interactive=False, lines=12, max_lines=25)

    def replay(demo_key: str, policy_key: str) -> tuple[str, str, str]:
        content = evidence_content(assets, files, demo_key, policy_key)
        return content.status, content.identity, content.trace_text

    gr.on(triggers=[scenario.change, selection.change], fn=replay,
          inputs=[scenario, selection], outputs=[status, identity, trace], api_visibility='private')
