from typing import List
from seerAD.enum.utils import run_nxc

def run(method: str, extra_args: List[str]):
    run_nxc("smb", method, extra_args)
