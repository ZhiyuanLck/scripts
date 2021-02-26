#!/usr/bin/env python

import logging
import pickle
import shlex
import click
from subprocess import Popen, PIPE, CalledProcessError, check_output, STDOUT
from functools import partial
from rich.logging import RichHandler
from rich.console import Console
from pathlib import Path


console = Console()


def run(cmd, **kwargs):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    with Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=1, text=True, **kwargs) as p:
        #  outs, errs = p.communicate()
        for line in p.stdout:
            print(line, end='')
        errs = p.stderr.read()
    if p.returncode != 0:
        raise CalledProcessError(p.returncode, p.args, stderr=errs)

logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

log = logging.getLogger()
fhandler = logging.FileHandler("install.log", mode="w")
fhandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="[%Y/%m/%d %I:%M:%S]"))
log.addHandler(fhandler)


@click.command()
def cli():
    p = Installer()


class Installer(object):
    def __init__(self, state_path=None, github=None):
        self.github = Path.home() / "github" if github is None else github
        self.config_dir = Path.home() / ".config"
        self.state_path = Path.cwd() / "state.p" if state_path is None else state_path
        if self.state_path.exists():
            with open(self.state_path, "rb") as f:
                self.state_dic = pickle.load(f)
        else:
            self._init_state()
        self._init_state()
        console.log(self.state_dic)
        self._install()
        with open(self.state_path, "wb") as f:
            pickle.dump(self.state_dic, f)

    def _init_state(self):
        self.state_dic = dict()
        self._init_rime()

    def _init_rime(self):
        self.state_dic["rime"] = {
                "ibus-rime": False,
                "config-path": False,
                "plum": False
                }

    def _install(self):
        self._install_rime()

    def _set(self, package, item):
        self.state_dic[package][item] = True

    def _do(self, package, item):
        return not self.state_dic[package][item]

    def _install_rime(self):
        log.info("Installing rime ...")
        config_path = self.config_dir / "ibus/rime"
        _set = partial(self._set, "rime")
        _do = partial(self._do, "rime")
        try:
            if _do("ibus-rime"):
                log.info("Installing ibus-rime ...")
                run("sudo apt install ibus-rime")
                _set("ibus-rime")

            if _do("config-path"):
                log.info(f"Creating directory {config_path} ...")
                if config_path.exists():
                    log.warning("Config directory exists, skip")
                else:
                    config_path.mkdir(parents=True)
                _set("config-path")

            if _do("plum"):
                log.info("Installing plum ...")
                plum = self.github / "plum"
                if plum.exists():
                    log.warning("Direcotry plum existed, skip")
                else:
                    run("git clone --depth 1 https://github.com/rime/plum.git", cwd=self.github)
                log.info("Installing schema ...")
                #  run("bash rime-install", cwd=plum)
                run("bash rime-install :preset pinyin-simp emoji:customize:schema=pinyin_simp", cwd=plum)
                #  run("bash rime-install emoji:customize:schema=double_pinyin_flypy", cwd=plum)
                _set("plum")

        except CalledProcessError as e:
            log.error(e.stderr)
            log.error("Installing rime failed")


if __name__ == '__main__':
    cli()
