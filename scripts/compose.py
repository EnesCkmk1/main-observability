"""Cross-platform Compose launcher that honors DYNATRACE_ENABLED."""

import subprocess
import sys

from ai_observability_lab.config import Settings

settings = Settings()
command = ["docker", "compose", "-f", "docker-compose.yml"]
if settings.dynatrace_enabled:
    command.extend(["-f", "docker-compose.dynatrace.yml"])
raise SystemExit(subprocess.call(command + (sys.argv[1:] or ["up", "-d", "--build", "--wait"])))
