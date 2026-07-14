##
## ====================== Installer ======================
##
import copy
import logging
import os
import subprocess
import sys

# Replacement for deprecated pkg_resources
try:
    from importlib.metadata import version as get_version, PackageNotFoundError
except ImportError:
    # Fallback for Python < 3.8
    import pkg_resources
    
KGEN_VERSION = "0.2.0"
python = sys.executable


def run(command) -> str:
    run_kwargs = {
        "args": command,
        "shell": True,
        "env": os.environ,
        "encoding": "utf8",
        "errors": "ignore",
    }
    run_kwargs["stdout"] = run_kwargs["stderr"] = subprocess.PIPE
    result = subprocess.run(**run_kwargs)

    if result.returncode != 0:
        raise RuntimeError()

    return result.stdout or ""


def run_pip(command):
    return run(f'"{python}" -m pip {command}')


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[0;36m",  # CYAN
        "INFO": "\033[0;32m",  # GREEN
        "WARNING": "\033[0;33m",  # YELLOW
        "ERROR": "\033[0;31m",  # RED
        "CRITICAL": "\033[0;37;41m",  # WHITE ON RED
        "RESET": "\033[0m",  # RESET COLOR
    }

    def format(self, record):
        colored_record = copy.copy(record)
        levelname = colored_record.levelname
        seq = self.COLORS.get(levelname, self.COLORS["RESET"])
        colored_record.levelname = f"{seq}{levelname}{self.COLORS['RESET']}"
        return super().format(colored_record)


# Create a new logger
logger = logging.getLogger("TIPO-KGen-installer")
logger.propagate = False

# Add handler if we don't have one.
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            "[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s", "%H:%M:%S"
        )
    )
    logger.addHandler(handler)

logger.setLevel(logging.INFO)
logger.debug("Logger initialized.")


def get_installed_version(package: str):
    try:
        if 'get_version' in globals():
            # importlib.metadata check
            return get_version(package)
        else:
            # Legacy pkg_resources check
            return pkg_resources.get_distribution(package).version
    except Exception:
        return None


# abetlen 公式の PEP503 wheel インデックス経由でインストールする。
# 0.3.34 以降は Python 版共通の py3-none wheel を配布しており、
# Python 3.13 を含む全バージョンを1つの wheel でカバーできる。
LLAMA_CPP_TARGET = "0.3.34"
# 0.3.34 で供給されている CUDA arch (whl index の variant 名 cuXXX の数値部分)
LLAMA_CPP_CUDA_ARCHS = [118, 121, 122, 123, 124, 125, 130, 132]
LLAMA_INDEX = "https://abetlen.github.io/llama-cpp-python/whl/{variant}"


def _version_tuple(v):
    """'0.3.34' のようなバージョン文字列を比較可能な数値タプルに変換する。
    文字列比較だと '0.3.4' > '0.3.34' と誤判定するため使う。"""
    parts = []
    for p in str(v).split(".")[:3]:
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _select_cuda_variant(cuda_version):
    """torch が報告する CUDA バージョン (例 '12.6') から、abetlen が供給する
    最も近い arch (検出値以下で最大) を選ぶ。低 CUDA 向け wheel は上位ドライバで
    動くが逆は不可のため round-down する。CUDA 無しは 'cpu'。"""
    if not cuda_version:
        return "cpu"
    major, _, minor = cuda_version.partition(".")
    try:
        detected = int(major) * 10 + int(minor or 0)
    except ValueError:
        return "cpu"
    candidates = [a for a in LLAMA_CPP_CUDA_ARCHS if a <= detected]
    arch = max(candidates) if candidates else min(LLAMA_CPP_CUDA_ARCHS)
    return f"cu{arch}"


def install_llama_cpp():
    # 目標版以上が既に import できる環境 (自作 CUDA ビルド等) は尊重してスキップ。
    # import 不可 or 旧版のときだけ導入する。
    try:
        import llama_cpp  # noqa: F401

        installed = get_installed_version("llama_cpp_python")
        if installed is not None and _version_tuple(installed) >= _version_tuple(
            LLAMA_CPP_TARGET
        ):
            return
    except Exception:
        pass

    logger.info("Attempting to install LLaMA-CPP-Python")
    import torch

    if torch.cuda.is_available() and torch.version.cuda:
        variant = _select_cuda_variant(torch.version.cuda)
    else:
        # macOS/Metal は対象外。非 CUDA 環境は CPU ビルドにフォールバックする。
        variant = "cpu"

    index = LLAMA_INDEX.format(variant=variant)
    try:
        run_pip(
            f'install -U "llama-cpp-python>={LLAMA_CPP_TARGET}" '
            f"--prefer-binary --extra-index-url {index}"
        )
        logger.info(f"Installation of llama-cpp-python ({variant}) succeeded")
    except Exception:
        logger.warning(
            "Installation of llama-cpp-python failed, "
            "Please try to install it manually or use non-gguf models"
        )


def install_tipo_kgen():
    version = get_installed_version("tipo-kgen")
    if version is not None and version >= KGEN_VERSION:
        return
    logger.info("Attempting to install tipo_kgen")
    run_pip(f'install -U "tipo-kgen>={KGEN_VERSION}"')
