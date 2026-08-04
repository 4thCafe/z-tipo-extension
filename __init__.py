"""ComfyUI entry point. A1111 and Forge load install.py and scripts/tipo.py instead."""

from comfy_api.latest import ComfyExtension, io


class TipoExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        from .nodes.tipo import NODES

        return NODES


async def comfy_entrypoint() -> ComfyExtension:
    return TipoExtension()
