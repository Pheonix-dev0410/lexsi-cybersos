from typing import Any

from cybersos.app.app_assets import AppAssets
from cybersos.app.practice_content import FACTOR_CHOICES, PROFILE_CHOICES, practice_content


def build_practice_view(assets: AppAssets) -> None:
    import gradio as gr

    initial = practice_content(assets)
    gr.Markdown('### C · Preparedness\nSynthetic dependency drill. Remove one factor and recompute '
                'the recovery routes. These are observable dependencies, not recovery predictions.')
    profile = gr.Dropdown(choices=PROFILE_CHOICES, value='single_phone', label='Synthetic profile')
    factor = gr.Radio(choices=FACTOR_CHOICES, value='phone', label='Remove one factor')
    run = gr.Button('Recompute routes')
    description = gr.Textbox(initial.profile, label='Synthetic access profile', interactive=False)
    with gr.Row():
        before = gr.Textbox('\n'.join(initial.before_routes), label='Reachable before removal',
                            interactive=False, lines=4)
        after = gr.Textbox('\n'.join(initial.after_routes), label='Reachable after removal',
                           interactive=False, lines=4)
    gap = gr.Textbox(initial.gap, label='Concrete dependency gap', interactive=False, lines=4)
    preparation = gr.Textbox(initial.preparation, label='Official preparation step', interactive=False)
    links = gr.Markdown('\n\n'.join(f'[{link.title}]({link.url})' for link in initial.sources))

    def recompute(profile_key: str, removed_factor: str) -> tuple[Any, ...]:
        content = practice_content(assets, profile_key, removed_factor)
        return (content.profile, '\n'.join(content.before_routes), '\n'.join(content.after_routes),
                content.gap, content.preparation,
                '\n\n'.join(f'[{link.title}]({link.url})' for link in content.sources))

    run.click(recompute, inputs=[profile, factor], outputs=[description, before, after, gap, preparation, links],
              api_visibility='private')
