from typing import Any

from cybersos.app.app_assets import AppAssets
from cybersos.app.incident_content import incident_content
from cybersos.app.incident_session import IncidentSession, start_incident
from cybersos.app.serving_policy import ServingModel


def build_incident_view(assets: AppAssets, serving: ServingModel) -> None:
    import gradio as gr

    gr.Markdown('Personal Google accounts and Android devices. Choose an incident to confirm scope '
                'and answer one availability question at a time. Never enter passwords or verification values.')
    state = gr.State(None, time_to_live=1800)
    with gr.Row():
        with gr.Column(variant='panel'):
            gr.Markdown('### Locked out\nLost a sign-in factor for your personal Google Account.')
            account = gr.Button('Plan account recovery')
        with gr.Column(variant='panel'):
            gr.Markdown('### Missing Android phone\nExplore official device protection and recovery.')
            android = gr.Button('Plan Android recovery')
        with gr.Column(variant='panel'):
            gr.Markdown('### Password exposed\nUse remaining safe access to contain the incident.')
            exposed = gr.Button('Plan containment')
    status = gr.Textbox(label='Guidance status', interactive=False)
    policy = gr.Textbox(value=serving.label, label='Policy actually serving', interactive=False)
    question = gr.Textbox(label='One access question', interactive=False, visible=False)
    answer = gr.Radio(label='Availability only', choices=[], visible=False)
    answer_button = gr.Button('Answer', visible=False)
    with gr.Group():
        instruction = gr.Textbox(label='What to do', interactive=False, visible=False)
        needs = gr.Textbox(label='What you need', interactive=False, visible=False)
        sources = gr.Markdown(visible=False)
        failure = gr.Textbox(label='What to report if it fails', interactive=False, visible=False)
        result = gr.Radio(choices=[('Completed / access available', 'success'),
                                   ('More verification requested', 'challenge'),
                                   ('Waiting for provider review', 'pending_review'),
                                   ('Unable to complete / denied', 'denial')],
                          label='Your reported result (never independently verified)', visible=False)
        report_button = gr.Button('Report result', visible=False)
    with gr.Accordion('Current known access', open=True):
        facts = gr.Dataframe(headers=['Access', 'Reported availability', 'Basis'],
                             datatype=['str', 'str', 'str'], interactive=False)
    with gr.Accordion('Try synthetic inputs without personal information', open=False):
        demo_choice = gr.Radio(choices=[('A · Circular dependency', 'circular'),
                                       ('B · Useful containment', 'containment')], value='circular',
                              label='Synthetic incident demo')
        demo_button = gr.Button('Load synthetic incident')
        gr.Markdown('C · Preparedness is ready in the Practice drill tab. All three recorded runs '
                    'are available in Evidence.')
    clear = gr.Button('Clear this session')
    outputs = [state, status, policy, question, answer, answer_button, instruction,
               needs, sources, failure, result, report_button, facts]

    def display(session: IncidentSession | None) -> tuple[Any, ...]:
        if session is None:
            return (None, '', serving.label,
                    gr.update(value='', visible=False), gr.update(value=None, visible=False),
                    gr.update(visible=False), *[gr.update(value='', visible=False) for _ in range(4)],
                    gr.update(value=None, visible=False), gr.update(visible=False), [])
        content = incident_content(session)
        asking, stepping = bool(content.question), bool(content.instruction)
        links = '\n\n'.join(f'[{link.title}]({link.url})' for link in content.sources)
        return (session, content.status, content.policy,
                gr.update(value=content.question, visible=asking),
                gr.update(choices=list(content.choices), value=None, visible=asking),
                gr.update(visible=asking), gr.update(value=content.instruction, visible=stepping),
                gr.update(value=content.needs, visible=stepping), gr.update(value=links, visible=stepping),
                gr.update(value=content.failure, visible=stepping),
                gr.update(value=None, visible=stepping), gr.update(visible=stepping), content.known_access)

    def begin(entry: str) -> tuple[Any, ...]:
        return display(start_incident(assets, entry, serving))

    def load_demo(key: str) -> tuple[Any, ...]:
        return display(start_incident(assets, 'account', serving, demo_key=key))

    def submit(session: IncidentSession | None, value: str | None, *, report: bool) -> tuple[Any, ...]:
        if session is not None and value is not None:
            try:
                session.report(value) if report else session.answer(value)
            except (ValueError, KeyError):
                gr.Warning('Choose an answer for the current question or step.')
        return display(session)

    def answer_current(session: IncidentSession | None, value: str | None) -> tuple[Any, ...]:
        return submit(session, value, report=False)

    def report_current(session: IncidentSession | None, value: str | None) -> tuple[Any, ...]:
        return submit(session, value, report=True)

    for button, entry in ((account, 'account'), (android, 'android'), (exposed, 'exposed')):
        button.click(begin, inputs=[gr.State(entry)], outputs=outputs, api_visibility='private')
    demo_button.click(load_demo, inputs=[demo_choice], outputs=outputs, api_visibility='private')
    answer_button.click(answer_current, inputs=[state, answer], outputs=outputs, api_visibility='private')
    report_button.click(report_current, inputs=[state, result], outputs=outputs, api_visibility='private')
    clear.click(display, inputs=[gr.State(None)], outputs=outputs, api_visibility='private')
