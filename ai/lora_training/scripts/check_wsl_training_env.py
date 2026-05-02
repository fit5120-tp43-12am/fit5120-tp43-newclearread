#!/usr/bin/env python3
"""Check the ClearRead WSL Llama LoRA training environment."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


PACKAGE_MODULES = {
    "torch": "torch",
    "transformers": "transformers",
    "datasets": "datasets",
    "accelerate": "accelerate",
    "peft": "peft",
    "trl": "trl",
    "bitsandbytes": "bitsandbytes",
    "unsloth": "unsloth",
    "huggingface_hub": "huggingface_hub",
    "safetensors": "safetensors",
    "sentencepiece": "sentencepiece",
}

HF_MODEL_IDS = [
    "unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit",
    "unsloth/Llama-3.1-8B-Instruct-bnb-4bit",
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
]


def distribution_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def import_status(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - report import failures exactly.
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "ok": True,
        "module_file": getattr(module, "__file__", None),
    }


def check_unsloth_import_order() -> dict[str, Any]:
    code = "import unsloth; import transformers; print('ok')"
    completed = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": completed.returncode == 0 and "ok" in completed.stdout,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.strip().splitlines()[-5:],
        "stderr_tail": completed.stderr.strip().splitlines()[-10:],
    }


def check_torch() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:  # noqa: BLE001 - report import failures exactly.
        return {
            "import_ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    cuda_available = bool(torch.cuda.is_available())
    result: dict[str, Any] = {
        "import_ok": True,
        "version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cuda_available": cuda_available,
        "cuda_device_count": int(torch.cuda.device_count()),
        "bf16_supported": bool(torch.cuda.is_bf16_supported()) if cuda_available else False,
    }
    if cuda_available:
        props = torch.cuda.get_device_properties(0)
        result.update(
            {
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_total_vram_bytes": int(props.total_memory),
                "gpu_total_vram_mib": round(int(props.total_memory) / 1024 / 1024, 2),
                "gpu_capability": list(torch.cuda.get_device_capability(0)),
            }
        )
        try:
            test_tensor = torch.ones((1,), device="cuda")
            result["cuda_tensor_test"] = float(test_tensor.item())
        except Exception as exc:  # noqa: BLE001 - report CUDA runtime failures exactly.
            result["cuda_tensor_test_error"] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
    return result


def hf_cli_status() -> dict[str, Any]:
    hf_path = shutil.which("hf")
    result: dict[str, Any] = {
        "hf_cli_available": hf_path is not None,
        "hf_cli_path": hf_path,
    }
    if hf_path is None:
        return result

    completed = subprocess.run(
        ["hf", "auth", "whoami"],
        text=True,
        capture_output=True,
        check=False,
    )
    result.update(
        {
            "whoami_ok": completed.returncode == 0,
            "whoami_returncode": completed.returncode,
            "whoami_stdout": completed.stdout.strip(),
            "whoami_stderr": completed.stderr.strip(),
        }
    )
    return result


def hf_model_info_status() -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # noqa: BLE001 - report import failures exactly.
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "models": {},
        }

    api = HfApi()
    models: dict[str, Any] = {}
    for model_id in HF_MODEL_IDS:
        try:
            info = api.model_info(model_id)
        except Exception as exc:  # noqa: BLE001 - access errors are expected evidence.
            models[model_id] = {
                "accessible": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            continue
        models[model_id] = {
            "accessible": True,
            "private": bool(getattr(info, "private", False)),
            "gated": getattr(info, "gated", None),
            "sha": getattr(info, "sha", None),
            "last_modified": str(getattr(info, "last_modified", "")),
        }
    return {
        "ok": True,
        "models": models,
    }


def build_report(include_hf: bool) -> dict[str, Any]:
    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "platform": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "environment": {
            "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
            "conda_prefix": os.environ.get("CONDA_PREFIX"),
        },
        "torch": check_torch(),
        "package_versions": {
            package: distribution_version(package)
            for package in PACKAGE_MODULES
        },
        "unsloth_before_transformers_fresh_process": check_unsloth_import_order(),
    }

    # Import Unsloth before Transformers/PEFT/TRL in this process too.
    ordered_modules = [
        "unsloth",
        "transformers",
        "datasets",
        "accelerate",
        "peft",
        "trl",
        "bitsandbytes",
        "huggingface_hub",
        "safetensors",
        "sentencepiece",
    ]
    report["import_checks"] = {
        module: import_status(module)
        for module in ordered_modules
    }

    if include_hf:
        report["huggingface"] = {
            "cli": hf_cli_status(),
            "model_info": hf_model_info_status(),
        }

    critical_imports = all(
        report["import_checks"].get(module, {}).get("ok", False)
        for module in ordered_modules
    )
    torch_ok = bool(report["torch"].get("import_ok")) and bool(report["torch"].get("cuda_available"))
    order_ok = bool(report["unsloth_before_transformers_fresh_process"].get("ok"))
    report["overall_ok"] = bool(torch_ok and critical_imports and order_ok)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hf-check",
        action="store_true",
        help="Also check Hugging Face CLI auth and metadata-only model access.",
    )
    args = parser.parse_args()

    report = build_report(include_hf=args.hf_check)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
