from typing import List
from seerAD.enum.utils import run_impacket

def run(method: str, extra_args: List[str]):
    run_impacket("GetUserSPNs", method, extra_args)