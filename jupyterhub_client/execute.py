import uuid
import difflib

from jupyterhub_client.api import JupyterHubAPI, JupyterKernelAPI
from jupyterhub_client.utils import parse_notebook_cells


async def execute_code(hub_url, cells, username=None, username_format='user-{id}', timeout=None):
    username = username or username_format.format(id=str(uuid.uuid4()))
    hub = JupyterHubAPI(hub_url)

    async with hub:
        try:
            await hub.create_user(username)
            jupyter = await hub.create_server(username)
            async with jupyter:
                kernel_id = (await jupyter.create_kernel())['id']
                async with JupyterKernelAPI(jupyter.api_url / 'kernels' / kernel_id, jupyter.api_token) as kernel:
                    for i, (code, expected_result) in enumerate(cells):
                        kernel_result = await kernel.send_code(username, code, timeout=timeout)
                        if kernel_result != expected_result:
                            diff = ''.join(difflib.unified_diff(kernel_result, expected_result))
                            raise ValueError(f'execution of cell={i} code={code} did not match expected result diff={diff}')
                await jupyter.delete_kernel(kernel_id)
            await hub.delete_server(username)
        finally:
            await hub.delete_user(username)


async def execute_notebook(hub_url, notebook_path, username=None, username_format='user-{id}', timeout=None):
    cells = parse_notebook_cells(notebook_path)
    await execute_code(hub_url, cells, username=username, username_format=username_format, timeout=timeout)
