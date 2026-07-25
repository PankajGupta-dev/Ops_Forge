import re
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from app.utils.logger import get_logger

logger = get_logger()

class DockerfileAnalysis(BaseModel):
    runtime: Optional[str] = None
    base_image: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    working_dir: Optional[str] = None
    exposed_ports: List[int] = []
    entry_command: Optional[List[str]] = None
    entrypoint: Optional[List[str]] = None
    package_manager: Optional[str] = None
    healthcheck: Optional[str] = None
    env_vars: Dict[str, str] = {}

def parse_dockerfile(dockerfile_content: str) -> DockerfileAnalysis:
    """
    Deterministically parses a Dockerfile string without using an LLM.
    Extracts explicit directives and infers runtime/language/package manager only if unambiguous.
    Unspecified fields are left as None/empty.
    """
    if not dockerfile_content or not dockerfile_content.strip():
        logger.warning("Empty Dockerfile content passed to parser.")
        return DockerfileAnalysis()

    lines = dockerfile_content.splitlines()
    
    base_image: Optional[str] = None
    working_dir: Optional[str] = None
    exposed_ports: List[int] = []
    entry_command: Optional[List[str]] = None
    entrypoint: Optional[List[str]] = None
    healthcheck: Optional[str] = None
    env_vars: Dict[str, str] = {}
    
    full_text = dockerfile_content.lower()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # FROM instruction
        if stripped.upper().startswith("FROM "):
            parts = stripped.split()
            if len(parts) >= 2:
                # Take the last FROM if multi-stage, or first non-builder
                img = parts[1]
                if " as " not in stripped.lower() or not base_image:
                    base_image = img

        # WORKDIR instruction
        elif stripped.upper().startswith("WORKDIR "):
            working_dir = stripped.split(maxsplit=1)[1].strip()

        # EXPOSE instruction
        elif stripped.upper().startswith("EXPOSE "):
            ports_str = stripped.split(maxsplit=1)[1].strip()
            for p in re.findall(r'\b\d+\b', ports_str):
                try:
                    port_int = int(p)
                    if port_int not in exposed_ports and 1 <= port_int <= 65535:
                        exposed_ports.append(port_int)
                except ValueError:
                    pass

        # ENV instruction
        elif stripped.upper().startswith("ENV "):
            env_line = stripped[4:].strip()
            # Supports ENV KEY=VAL or ENV KEY VAL
            if "=" in env_line:
                k, v = env_line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"\'')
            else:
                parts = env_line.split(maxsplit=1)
                if len(parts) == 2:
                    env_vars[parts[0].strip()] = parts[1].strip().strip('"\'')

        # CMD instruction
        elif stripped.upper().startswith("CMD "):
            cmd_body = stripped[4:].strip()
            if cmd_body.startswith("[") and cmd_body.endswith("]"):
                entry_command = [item.strip().strip('"\'') for item in cmd_body[1:-1].split(",") if item.strip()]
            else:
                entry_command = cmd_body.split()

        # ENTRYPOINT instruction
        elif stripped.upper().startswith("ENTRYPOINT "):
            ep_body = stripped[11:].strip()
            if ep_body.startswith("[") and ep_body.endswith("]"):
                entrypoint = [item.strip().strip('"\'') for item in ep_body[1:-1].split(",") if item.strip()]
            else:
                entrypoint = ep_body.split()

        # HEALTHCHECK instruction
        elif stripped.upper().startswith("HEALTHCHECK "):
            healthcheck = stripped[12:].strip()

    # Determine runtime & language deterministically from base_image
    runtime: Optional[str] = None
    language: Optional[str] = None
    package_manager: Optional[str] = None
    framework: Optional[str] = None

    if base_image:
        base_lower = base_image.lower()
        if "python" in base_lower:
            runtime = "python"
            language = "python"
            package_manager = "pip"
        elif "node" in base_lower:
            runtime = "node"
            language = "javascript/typescript"
            package_manager = "npm"
        elif "golang" in base_lower or "go:" in base_lower or base_lower == "golang":
            runtime = "go"
            language = "go"
        elif "openjdk" in base_lower or "maven" in base_lower or "gradle" in base_lower:
            runtime = "java"
            language = "java"
            if "maven" in base_lower:
                package_manager = "maven"
            elif "gradle" in base_lower:
                package_manager = "gradle"
        elif "rust" in base_lower:
            runtime = "rust"
            language = "rust"
            package_manager = "cargo"
        elif "ruby" in base_lower:
            runtime = "ruby"
            language = "ruby"
            package_manager = "bundler"
        elif "php" in base_lower:
            runtime = "php"
            language = "php"
            package_manager = "composer"
        elif "nginx" in base_lower or "alpine" in base_lower or "ubuntu" in base_lower:
            if "nginx" in base_lower:
                runtime = "static"

    # Infer framework if obvious in instructions/command
    if "fastapi" in full_text or "uvicorn" in full_text:
        framework = "fastapi"
        if not language:
            language = "python"
            runtime = "python"
    elif "django" in full_text:
        framework = "django"
        if not language:
            language = "python"
            runtime = "python"
    elif "flask" in full_text:
        framework = "flask"
        if not language:
            language = "python"
            runtime = "python"
    elif "express" in full_text or "next" in full_text or "nest" in full_text:
        if "next" in full_text:
            framework = "nextjs"
        elif "nest" in full_text:
            framework = "nestjs"
        else:
            framework = "express"
        if not language:
            language = "javascript/typescript"
            runtime = "node"

    # Package manager secondary check
    if "poetry" in full_text:
        package_manager = "poetry"
    elif "pipenv" in full_text:
        package_manager = "pipenv"
    elif "yarn" in full_text:
        package_manager = "yarn"
    elif "pnpm" in full_text:
        package_manager = "pnpm"

    analysis = DockerfileAnalysis(
        runtime=runtime,
        base_image=base_image,
        language=language,
        framework=framework,
        working_dir=working_dir,
        exposed_ports=exposed_ports,
        entry_command=entry_command,
        entrypoint=entrypoint,
        package_manager=package_manager,
        healthcheck=healthcheck,
        env_vars=env_vars,
    )

    logger.info(f"Dockerfile parsed successfully. Runtime: {runtime}, Base: {base_image}, Ports: {exposed_ports}")
    return analysis
